grokfinfizbreakoit.java
### Updated Spring Boot Java Application with Database Persistence

I've updated the application to add database persistence using Spring Data JPA and H2 database (embedded, file-based for persistence). This ensures the `previousTickers` state is stored in a database and survives app restarts.

#### Key Changes
- **Dependencies**: Added `spring-boot-starter-data-jpa` and `h2` (runtime).
- **Entity**: Created `PreviousTicker` entity with `ticker` as `@Id`.
- **Repository**: `PreviousTickerRepository` extends `JpaRepository`.
- **Service Updates**:
  - Load `previousTickers` from DB at the start of each monitoring run.
  - At the end, clear the DB and save the current tickers.
- **Configuration**: In `application.yml`, added Spring DataSource for H2 (file-based: `./data/finviz` to persist on disk).
- **Initialization**: On first run or if empty, previousTickers is empty.
- **Notes**: H2 is used for simplicity (no external DB needed). For production, switch to PostgreSQL by changing dependencies and config. The DB file will be created in the project root under `./data`.

#### Updated `pom.xml`
```xml


    4.0.0

    com.example
    finviz-monitor
    1.0.0
    jar

    
        org.springframework.boot
        spring-boot-starter-parent
        3.2.0
        
    

    
        17
        1.17.2
    

    
        
            org.springframework.boot
            spring-boot-starter-web
        
        
            org.springframework.boot
            spring-boot-starter-data-jpa
        
        
            com.h2database
            h2
            runtime
        
        
            org.jsoup
            jsoup
            ${jsoup.version}
        
        
            org.springframework.boot
            spring-boot-starter-test
            test
        
        
            org.projectlombok
            lombok
            true
        
    

    
        
            
                org.springframework.boot
                spring-boot-maven-plugin
            
        
    

Updated `application.yml`
spring:
  application:
    name: finviz-monitor
  datasource:
    url: jdbc:h2:file:./data/finviz;DB_CLOSE_ON_EXIT=FALSE;AUTO_SERVER=TRUE
    username: sa
    password: password
    driver-class-name: org.h2.Driver
  jpa:
    hibernate:
      ddl-auto: update  # Creates/updates tables automatically
    show-sql: true
    properties:
      hibernate:
        dialect: org.hibernate.dialect.H2Dialect

logging:
  level:
    com.example.finviz: INFO
    root: WARN
    org.hibernate.SQL: DEBUG  # Optional: Log SQL queries

app:
  finviz-url: https://finviz.com/screener.ashx?v=111&f=sh_opt_optionshort%2Csh_outstanding_u20%2Csh_relvol_o1.5%2Csh_short_o30
  monitor-interval: 300000  # 5 minutes in ms
`entity/PreviousTicker.java` (New File)
package com.example.finviz.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import lombok.Data;

@Entity
@Data
public class PreviousTicker {
    @Id
    private String ticker;
}
`repository/PreviousTickerRepository.java` (New File)
package com.example.finviz.repository;

import com.example.finviz.entity.PreviousTicker;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface PreviousTickerRepository extends JpaRepository {
}
Updated `service/TickerMonitorService.java`
package com.example.finviz.service;

import com.example.finviz.entity.PreviousTicker;
import com.example.finviz.model.TickerData;
import com.example.finviz.repository.PreviousTickerRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashSet;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class TickerMonitorService {

    private final RestTemplate restTemplate = new RestTemplate();
    private final PreviousTickerRepository previousTickerRepository;

    @Value("${app.finviz-url}")
    private String finvizUrl;

    @Value("${app.monitor-interval}")
    private long monitorInterval;

    @Scheduled(fixedRateString = "${app.monitor-interval}")
    public void monitorTickerChanges() {
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        log.info("=== Finviz Monitor Run at {} ===", timestamp);

        // Fetch and parse current tickers
        Set currentTickers = fetchCurrentTickers();
        if (currentTickers.isEmpty()) {
            log.warn("No tickers fetched. Check URL or connectivity.");
            return;
        }

        Set currentTickerSymbols = currentTickers.stream()
                .map(TickerData::getTicker)
                .collect(Collectors.toSet());

        // Load previous tickers from DB
        Set previousTickers = previousTickerRepository.findAll().stream()
                .map(PreviousTicker::getTicker)
                .collect(Collectors.toSet());

        // Detect changes
        Set added = new HashSet<>(currentTickerSymbols);
        added.removeAll(previousTickers);
        Set dropped = new HashSet<>(previousTickers);
        dropped.removeAll(currentTickerSymbols);

        if (!added.isEmpty()) {
            log.info("ADDED Tickers ({}): {}", added.size(), added);
        }
        if (!dropped.isEmpty()) {
            log.info("DROPPED Tickers ({}): {}", dropped.size(), dropped);
        }
        if (added.isEmpty() && dropped.isEmpty()) {
            log.info("No changes detected. Total tickers: {}", currentTickerSymbols.size());
        }

        // Log sample details for added/dropped
        added.forEach(ticker -> logTickerDetails(ticker, currentTickers));
        dropped.forEach(ticker -> log.info("Dropped: {}", ticker));  // Details not available for dropped

        // Update DB: Clear and save current
        previousTickerRepository.deleteAll();
        currentTickerSymbols.forEach(ticker -> {
            PreviousTicker pt = new PreviousTicker();
            pt.setTicker(ticker);
            previousTickerRepository.save(pt);
        });

        // Check total count (from page, approximate)
        int totalCount = estimateTotalCount();
        log.info("Estimated total results on Finviz: {}", totalCount);
        if (totalCount > 20) {
            log.warn("Only first page (20 tickers) monitored. Implement pagination for full coverage.");
        }

        log.info("=== End Run ===");
    }

    private Set fetchCurrentTickers() {
        try {
            String html = restTemplate.getForObject(finvizUrl, String.class);
            Document doc = Jsoup.parse(html);
            Elements rows = doc.select("table.screener_table tbody tr");  // Adjust selector based on Finviz HTML

            Set tickers = new HashSet<>();
            for (Element row : rows) {
                Elements cells = row.select("td");
                if (cells.size() < 10) continue;  // Skip invalid rows

                TickerData data = new TickerData();
                data.setTicker(cells.get(1).select("a").text().trim());  // Ticker in link
                data.setCompany(cells.get(2).text().trim());
                data.setSector(cells.get(3).text().trim());
                data.setIndustry(cells.get(4).text().trim());
                data.setCountry(cells.get(5).text().trim());
                data.setMarketCap(cells.get(6).text().trim());
                data.setPe(cells.get(7).text().trim().equals("-") ? "N/A" : cells.get(7).text().trim());
                data.setPrice(cells.get(8).text().trim());
                data.setChange(cells.get(9).text().trim());
                data.setVolume(cells.get(10).text().trim());
                tickers.add(data);
            }
            return tickers;
        } catch (Exception e) {
            log.error("Error fetching/parsing Finviz: {}", e.getMessage());
            return new HashSet<>();
        }
    }

    private void logTickerDetails(String ticker, Set tickers) {
        tickers.stream()
                .filter(t -> t.getTicker().equals(ticker))
                .findFirst()
                .ifPresent(t -> log.info("Details for {}: {} ({}) - Price: {}, Change: {}", 
                    t.getTicker(), t.getCompany(), t.getSector(), t.getPrice(), t.getChange()));
    }

    private int estimateTotalCount() {
        // Parse from HTML, e.g., look for text like "#1 / 10458 Total"
        try {
            String html = restTemplate.getForObject(finvizUrl, String.class);
            Document doc = Jsoup.parse(html);
            String totalText = doc.select("div#content > div > div > span").text();  // Improved selector; adjust if needed based on actual HTML
            if (totalText.contains("/")) {
                // Extract number after "/"
                String[] parts = totalText.split("/");
                if (parts.length > 1) {
                    return Integer.parseInt(parts[1].trim().replaceAll("[^0-9]", ""));
                }
            }
        } catch (Exception ignored) {}
        return 0;
    }
}
Other Files
	•	FinvizMonitorApplication.java, model/TickerData.java, and the test remain unchanged.
	•	New directories: entity/ and repository/.
How Persistence Works
	•	On app start, H2 creates the previous_ticker table if needed.
	•	Each run: Load from DB → Compare → Log changes → Update DB with current tickers.
	•	If app restarts, the last saved tickers are loaded from the ./data/finviz.mv.db file.
For PostgreSQL, replace H2 dependency with org.postgresql:postgresql, update application.yml datasource to PostgreSQL config, and set ddl-auto: update.
Build and run as before. The DB ensures state persistence! If you need further tweaks (e.g., adding timestamps), let me know.


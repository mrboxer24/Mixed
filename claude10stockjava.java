// pom.xml dependencies needed:
/*
<dependency>
<groupId>org.springframework.boot</groupId>
<artifactId>spring-boot-starter-web</artifactId>
</dependency>
<dependency>
<groupId>org.springframework.boot</groupId>
<artifactId>spring-boot-starter-data-jpa</artifactId>
</dependency>
<dependency>
<groupId>com.h2database</groupId>
<artifactId>h2</artifactId>
<scope>runtime</scope>
</dependency>
*/

// StockMonitoringApplication.java
package com.stockmonitor;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class StockMonitoringApplication {
public static void main(String[] args) {
SpringApplication.run(StockMonitoringApplication.class, args);
}
}

// Stock.java - Entity
package com.stockmonitor.entity;

import javax.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = “stocks”)
public class Stock {
@Id
@GeneratedValue(strategy = GenerationType.IDENTITY)
private Long id;

```
@Column(unique = true, nullable = false)
private String symbol;

@Column(name = "company_name")
private String companyName;

@Column(name = "current_price", precision = 10, scale = 2)
private BigDecimal currentPrice;

@Column(name = "previous_price", precision = 10, scale = 2)
private BigDecimal previousPrice;

@Column(name = "last_updated")
private LocalDateTime lastUpdated;

@Column(name = "is_active")
private Boolean isActive = true;

// Constructors
public Stock() {}

public Stock(String symbol, String companyName) {
    this.symbol = symbol;
    this.companyName = companyName;
    this.isActive = true;
}

// Getters and Setters
public Long getId() { return id; }
public void setId(Long id) { this.id = id; }

public String getSymbol() { return symbol; }
public void setSymbol(String symbol) { this.symbol = symbol; }

public String getCompanyName() { return companyName; }
public void setCompanyName(String companyName) { this.companyName = companyName; }

public BigDecimal getCurrentPrice() { return currentPrice; }
public void setCurrentPrice(BigDecimal currentPrice) { this.currentPrice = currentPrice; }

public BigDecimal getPreviousPrice() { return previousPrice; }
public void setPreviousPrice(BigDecimal previousPrice) { this.previousPrice = previousPrice; }

public LocalDateTime getLastUpdated() { return lastUpdated; }
public void setLastUpdated(LocalDateTime lastUpdated) { this.lastUpdated = lastUpdated; }

public Boolean getIsActive() { return isActive; }
public void setIsActive(Boolean isActive) { this.isActive = isActive; }
```

}

// StockRepository.java
package com.stockmonitor.repository;

import com.stockmonitor.entity.Stock;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface StockRepository extends JpaRepository<Stock, Long> {
Optional<Stock> findBySymbol(String symbol);
List<Stock> findByIsActiveTrue();
}

// StockPriceService.java - External API integration
package com.stockmonitor.service;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.beans.factory.annotation.Value;
import java.math.BigDecimal;
import java.util.Map;

@Service
public class StockPriceService {

```
private final RestTemplate restTemplate;

// You'll need to get a free API key from Alpha Vantage or similar service
@Value("${stock.api.key:demo}")
private String apiKey;

@Value("${stock.api.url:https://www.alphavantage.co/query}")
private String apiUrl;

public StockPriceService() {
    this.restTemplate = new RestTemplate();
}

public BigDecimal getCurrentPrice(String symbol) {
    try {
        // Alpha Vantage API call
        String url = String.format("%s?function=GLOBAL_QUOTE&symbol=%s&apikey=%s", 
                                 apiUrl, symbol, apiKey);
        
        Map<String, Object> response = restTemplate.getForObject(url, Map.class);
        
        if (response != null && response.containsKey("Global Quote")) {
            Map<String, String> quote = (Map<String, String>) response.get("Global Quote");
            String priceStr = quote.get("05. price");
            return new BigDecimal(priceStr);
        }
        
        // Fallback: Mock data for demo purposes
        return getMockPrice(symbol);
        
    } catch (Exception e) {
        System.err.println("Error fetching price for " + symbol + ": " + e.getMessage());
        return getMockPrice(symbol);
    }
}

// Mock prices for testing (remove when using real API)
private BigDecimal getMockPrice(String symbol) {
    Map<String, BigDecimal> mockPrices = Map.of(
        "APP", new BigDecimal("245.50"),
        "CLS", new BigDecimal("78.25"),
        "PLTR", new BigDecimal("42.80"),
        "RGTI", new BigDecimal("12.45"),
        "NVDA", new BigDecimal("875.25"),
        "HOOD", new BigDecimal("28.50"),
        "VRT", new BigDecimal("105.75"),
        "CVNA", new BigDecimal("185.30"),
        "IONQ", new BigDecimal("15.85"),
        "RKLB", new BigDecimal("22.40")
    );
    
    BigDecimal basePrice = mockPrices.getOrDefault(symbol, new BigDecimal("100.00"));
    // Add some random variation (-2% to +2%)
    double variation = (Math.random() - 0.5) * 0.04;
    return basePrice.multiply(BigDecimal.valueOf(1 + variation));
}
```

}

// AudioAlertService.java - Sound and speech alerts
package com.stockmonitor.service;

import org.springframework.stereotype.Service;
import javax.sound.sampled.*;
import javax.speech.Central;
import javax.speech.synthesis.Synthesizer;
import javax.speech.synthesis.SynthesizerModeDesc;
import java.io.ByteArrayInputStream;

@Service
public class AudioAlertService {

```
public void playAlertSound() {
    try {
        // Generate a simple beep sound
        byte[] buffer = new byte[1000];
        AudioFormat format = new AudioFormat(8000f, 8, 1, true, false);
        
        for (int i = 0; i < buffer.length; i++) {
            double angle = i / (8000f / 440) * 2.0 * Math.PI;
            buffer[i] = (byte)(Math.sin(angle) * 127);
        }
        
        AudioInputStream audioInputStream = new AudioInputStream(
            new ByteArrayInputStream(buffer), format, buffer.length);
        
        Clip clip = AudioSystem.getClip();
        clip.open(audioInputStream);
        clip.start();
        
        // Play multiple times for alert
        for (int i = 0; i < 3; i++) {
            clip.setFramePosition(0);
            clip.start();
            Thread.sleep(200);
        }
        
    } catch (Exception e) {
        System.err.println("Error playing alert sound: " + e.getMessage());
    }
}

public void speakAlert(String message) {
    try {
        // Note: For speech synthesis, you might need additional dependencies
        // or use system commands. This is a simplified version.
        System.out.println("🔊 ALERT: " + message);
        
        // Alternative: Use system TTS (works on Windows/Mac)
        String os = System.getProperty("os.name").toLowerCase();
        if (os.contains("win")) {
            // Windows PowerShell TTS
            Runtime.getRuntime().exec(new String[]{
                "powershell", "-Command", 
                "Add-Type -AssemblyName System.Speech; " +
                "$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; " +
                "$speak.Speak('" + message + "');"
            });
        } else if (os.contains("mac")) {
            // macOS say command
            Runtime.getRuntime().exec(new String[]{"say", message});
        } else {
            // Linux espeak (if installed)
            Runtime.getRuntime().exec(new String[]{"espeak", message});
        }
        
    } catch (Exception e) {
        System.err.println("Error with speech synthesis: " + e.getMessage());
    }
}
```

}

// StockMonitoringService.java - Main monitoring logic
package com.stockmonitor.service;

import com.stockmonitor.entity.Stock;
import com.stockmonitor.repository.StockRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import javax.annotation.PostConstruct;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;

@Service
public class StockMonitoringService {

```
@Autowired
private StockRepository stockRepository;

@Autowired
private StockPriceService priceService;

@Autowired
private AudioAlertService audioService;

// Stock symbols from your list
private final List<String> MONITORED_STOCKS = Arrays.asList(
    "APP",   // AppLovin
    "CLS",   // Celestica  
    "PLTR",  // Palantir
    "RGTI",  // Rigetti
    "IONQ",  // IonQ
    "VRT",   // Vertiv
    "CVNA",  // Carvana
    "NVDA",  // Nvidia
    "HOOD",  // Robinhood
    "RKLB"   // Rocket Lab
    // Add more symbols as needed
);

@PostConstruct
public void initializeStocks() {
    System.out.println("🚀 Initializing stock monitoring service...");
    
    for (String symbol : MONITORED_STOCKS) {
        if (stockRepository.findBySymbol(symbol).isEmpty()) {
            Stock stock = new Stock(symbol, getCompanyName(symbol));
            stockRepository.save(stock);
            System.out.println("📈 Added stock: " + symbol);
        }
    }
    
    System.out.println("✅ Stock monitoring service initialized!");
}

@Scheduled(fixedRate = 300000) // Every 5 minutes (300,000 ms)
public void monitorStocks() {
    System.out.println("🔍 Checking stock prices at " + LocalDateTime.now());
    
    List<Stock> activeStocks = stockRepository.findByIsActiveTrue();
    
    for (Stock stock : activeStocks) {
        try {
            BigDecimal newPrice = priceService.getCurrentPrice(stock.getSymbol());
            BigDecimal oldPrice = stock.getCurrentPrice();
            
            if (oldPrice != null && newPrice != null) {
                BigDecimal change = newPrice.subtract(oldPrice);
                BigDecimal changePercent = change.divide(oldPrice, 4, RoundingMode.HALF_UP)
                                               .multiply(BigDecimal.valueOf(100));
                
                System.out.printf("%s: $%.2f → $%.2f (%.2f%%)\n", 
                                stock.getSymbol(), oldPrice, newPrice, changePercent);
                
                // Check if it's a significant drop (3-5%)
                if (changePercent.compareTo(BigDecimal.valueOf(-3.0)) <= 0) {
                    handlePriceDrop(stock, oldPrice, newPrice, changePercent);
                }
            }
            
            // Update stock price
            stock.setPreviousPrice(stock.getCurrentPrice());
            stock.setCurrentPrice(newPrice);
            stock.setLastUpdated(LocalDateTime.now());
            stockRepository.save(stock);
            
        } catch (Exception e) {
            System.err.println("Error monitoring " + stock.getSymbol() + ": " + e.getMessage());
        }
    }
}

private void handlePriceDrop(Stock stock, BigDecimal oldPrice, BigDecimal newPrice, 
                            BigDecimal changePercent) {
    String alertMessage = String.format("%s has dropped %.2f%% from $%.2f to $%.2f", 
                                      stock.getSymbol(), 
                                      changePercent.abs(), 
                                      oldPrice, 
                                      newPrice);
    
    System.out.println("🚨 PRICE ALERT: " + alertMessage);
    
    // Play loud alert sound
    audioService.playAlertSound();
    
    // Speak the alert
    String speechMessage = String.format("%s ticker dropped %s percent", 
                                        stock.getSymbol(), 
                                        changePercent.abs().setScale(1, RoundingMode.HALF_UP));
    audioService.speakAlert(speechMessage);
}

private String getCompanyName(String symbol) {
    // Map symbols to company names
    return switch (symbol) {
        case "APP" -> "AppLovin Corporation";
        case "CLS" -> "Celestica Inc.";
        case "PLTR" -> "Palantir Technologies";
        case "RGTI" -> "Rigetti Computing";
        case "IONQ" -> "IonQ Inc.";
        case "VRT" -> "Vertiv Holdings";
        case "CVNA" -> "Carvana Co.";
        case "NVDA" -> "NVIDIA Corporation";
        case "HOOD" -> "Robinhood Markets";
        case "RKLB" -> "Rocket Lab USA";
        default -> symbol + " Inc.";
    };
}
```

}

// StockController.java - REST API endpoints
package com.stockmonitor.controller;

import com.stockmonitor.entity.Stock;
import com.stockmonitor.repository.StockRepository;
import com.stockmonitor.service.StockMonitoringService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping(”/api/stocks”)
public class StockController {

```
@Autowired
private StockRepository stockRepository;

@Autowired
private StockMonitoringService monitoringService;

@GetMapping
public List<Stock> getAllStocks() {
    return stockRepository.findAll();
}

@GetMapping("/active")
public List<Stock> getActiveStocks() {
    return stockRepository.findByIsActiveTrue();
}

@PostMapping("/monitor-now")
public String triggerMonitoring() {
    monitoringService.monitorStocks();
    return "Monitoring triggered manually";
}

@PutMapping("/{symbol}/toggle")
public String toggleStockMonitoring(@PathVariable String symbol) {
    Stock stock = stockRepository.findBySymbol(symbol.toUpperCase())
                               .orElseThrow(() -> new RuntimeException("Stock not found"));
    
    stock.setIsActive(!stock.getIsActive());
    stockRepository.save(stock);
    
    return String.format("Stock %s monitoring %s", symbol, 
                       stock.getIsActive() ? "enabled" : "disabled");
}
```

}
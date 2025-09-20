import React, { useState, useEffect } from 'react';
import { RSI, BollingerBands } from 'technicalindicators';

const BUY_AMOUNT = 2000;
const LOSS_THRESHOLD = 200;

const App = () => {
  const [portfolio, setPortfolio] = useState([]);
  const [sp500, setSp500] = useState(new Set());
  const [logs, setLogs] = useState([]);
  const [currentPrices, setCurrentPrices] = useState({});

  useEffect(() => {
    const loadSP500 = async () => {
      try {
        const url = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.json';
        const res = await fetch(url);
        const data = await res.json();
        const symbols = data.map(c => c.Symbol);
        setSp500(new Set(symbols));
        logMessage('Loaded S&P 500 tickers.');
      } catch (error) {
        logMessage('Error loading S&P 500: ' + error.message);
      }
    };
    loadSP500();
  }, []);

  useEffect(() => {
    if (sp500.size === 0) return;

    const interval = setInterval(() => {
      scanAndTrade();
    }, 5 * 60 * 1000); // Every 5 minutes

    scanAndTrade(); // Initial scan

    return () => clearInterval(interval);
  }, [sp500]);

  const logMessage = (msg) => {
    setLogs(prev => [...prev, `${new Date().toLocaleString()}: ${msg}`]);
  };

  const getTrending = async () => {
    try {
      const res = await fetch('https://query1.finance.yahoo.com/v1/finance/trending/US');
      const data = await res.json();
      return data.finance.result[0].quotes.map(q => q.symbol);
    } catch (error) {
      logMessage('Error fetching trending: ' + error.message);
      return [];
    }
  };

  const getHistorical = async (symbol) => {
    try {
      const period1 = Math.floor((Date.now() - 7 * 24 * 60 * 60 * 1000) / 1000); // Last 7 days
      const period2 = Math.floor(Date.now() / 1000);
      const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?period1=${period1}&period2=${period2}&interval=5m`;
      const res = await fetch(url);
      const data = await res.json();
      const timestamps = data.chart.result[0].timestamp;
      const quotes = data.chart.result[0].indicators.quote[0];
      return timestamps.map((t, i) => ({
        date: new Date(t * 1000),
        open: quotes.open[i],
        high: quotes.high[i],
        low: quotes.low[i],
        close: quotes.close[i],
        volume: quotes.volume[i]
      })).filter(q => q.close !== null);
    } catch (error) {
      logMessage(`Error fetching historical for ${symbol}: ${error.message}`);
      return [];
    }
  };

  const getQuote = async (symbol) => {
    try {
      const url = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${symbol}`;
      const res = await fetch(url);
      const data = await res.json();
      return data.quoteResponse.result[0].regularMarketPrice;
    } catch (error) {
      logMessage(`Error fetching quote for ${symbol}: ${error.message}`);
      return null;
    }
  };

  const checkBuyCondition = async (symbol) => {
    const history = await getHistorical(symbol);
    if (history.length < 50) return false;

    const closes = history.map(h => h.close).slice(-50);

    // Bollinger Bands
    const bbInput = { period: 20, stdDev: 2, values: closes };
    const bb = BollingerBands.calculate(bbInput);
    const lastBb = bb[bb.length - 1];
    const lastClose = closes[closes.length - 1];

    // RSI
    const rsiInput = { values: closes, period: 14 };
    const rsi = RSI.calculate(rsiInput);
    const lastRsi = rsi[rsi.length - 1];
    const prevRsi = rsi[rsi.length - 2];

    // Condition: RSI drops suddenly to below 30 (oversold) and price below lower Bollinger band
    const rsiDropped = lastRsi < 30 && prevRsi >= 30;
    const bbOutLower = lastClose < lastBb.lower;

    return rsiDropped && bbOutLower;
  };

  const updateCurrentPrices = async () => {
    const symbols = portfolio.map(p => p.symbol);
    if (symbols.length === 0) return;

    const newPrices = {};
    for (const symbol of symbols) {
      const price = await getQuote(symbol);
      if (price) newPrices[symbol] = price;
    }
    setCurrentPrices(newPrices);
  };

  const scanAndTrade = async () => {
    logMessage('Starting scan...');

    // Update current prices for portfolio
    await updateCurrentPrices();

    // Check sells
    const newPortfolio = [...portfolio];
    for (let i = newPortfolio.length - 1; i >= 0; i--) {
      const pos = newPortfolio[i];
      const currPrice = currentPrices[pos.symbol];
      if (!currPrice) continue;
      const currValue = currPrice * pos.shares;
      if (currValue <= BUY_AMOUNT - LOSS_THRESHOLD) {
        newPortfolio.splice(i, 1);
        logMessage(`Sold ${pos.symbol} at loss: current value ${currValue.toFixed(2)}`);
      }
    }
    setPortfolio(newPortfolio);

    // Get trending
    const trending = await getTrending();
    const sp500Trending = trending.filter(s => sp500.has(s));

    // Check buys
    for (const symbol of sp500Trending) {
      if (portfolio.some(p => p.symbol === symbol)) continue; // Already holding

      const shouldBuy = await checkBuyCondition(symbol);
      if (shouldBuy) {
        const currPrice = await getQuote(symbol);
        if (!currPrice) continue;
        const shares = BUY_AMOUNT / currPrice;
        const newPos = {
          symbol,
          buyPrice: currPrice,
          shares,
          buyValue: BUY_AMOUNT,
          buyTime: new Date()
        };
        setPortfolio(prev => [...prev, newPos]);
        logMessage(`Bought ${symbol} at ${currPrice.toFixed(2)}`);
      }
    }

    logMessage('Scan completed.');
  };

  return (
    
      
ReactJS Stock Portfolio Manager
      
Portfolio
      
          {portfolio.map((pos, index) => {
            const currPrice = currentPrices[pos.symbol] || pos.buyPrice;
            const currValue = currPrice * pos.shares;
            const gainLoss = currValue - pos.buyValue;
            return (
              
            );
          })}
        
        
          
            
Symbol
            
Buy Price
            
Shares
            
Current Price
            
Current Value
            
Gain/Loss
          
        
        
                
{pos.symbol}
                
{pos.buyPrice.toFixed(2)}
                
{pos.shares.toFixed(2)}
                
{currPrice.toFixed(2)}
                
{currValue.toFixed(2)}
                
= 0 ? 'green' : 'red' }}>{gainLoss.toFixed(2)}
              
      
      
Logs
      
        {logs.map((log, index) => (
          
{log}
        ))}
      
    
  );
};

export default App;
This is a basic implementation of a ReactJS stock portfolio manager with the requested features. It automatically scans Yahoo Finance trending tickers every 5 minutes, filters for S&P 500 stocks, and buys if there’s a sudden RSI drop to oversold (crossing below 30) combined with the price breaking out below the lower Bollinger Band. It buys $2000 worth of the stock and sells automatically if the position runs a loss of $200 or more.
Notes:
	•	Install dependencies: npm install technicalindicators
	•	The app uses direct Yahoo Finance API endpoints which should work in the browser (CORS is allowed by Yahoo).
	•	This is a simulation; it doesn’t connect to a real brokerage for actual trading.
	•	Error handling is basic; in production, add more robustness.
	•	Historical data is fetched for the last 7 days at 5-minute intervals for indicator calculations.
	•	Current prices are updated during each scan.
	•	The S&P 500 list is fetched from a public GitHub dataset (may not be real-time updated, but sufficient for demo).

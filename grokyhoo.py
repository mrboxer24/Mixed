#!/usr/bin/env python3
“””
Minimal Agentic AI: Yahoo Finance Day Gainers Monitor
Scans Yahoo Finance day gainers API every 15 minutes and announces new tickers
“””

import requests
import time
import threading
from datetime import datetime
import json
import os

# Text-to-speech imports (cross-platform)

try:
import pyttsx3
TTS_ENGINE = pyttsx3.init()
TTS_ENGINE.setProperty(‘rate’, 150)
TTS_ENGINE.setProperty(‘volume’, 1.0)
TTS_AVAILABLE = True
except ImportError:
print(“Warning: pyttsx3 not installed. Install with: pip install pyttsx3”)
TTS_AVAILABLE = False

class TickerMonitorAgent:
def **init**(self, api_url, check_interval=900):  # 900 seconds = 15 minutes
self.api_url = api_url
self.check_interval = check_interval
self.known_tickers = set()
self.state_file = “ticker_state.json”
self.running = False

```
    # Load previous state
    self.load_state()
    
def load_state(self):
    """Load previously seen tickers from file"""
    try:
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                self.known_tickers = set(data.get('tickers', []))
                print(f"Loaded {len(self.known_tickers)} known tickers from state file")
    except Exception as e:
        print(f"Error loading state: {e}")
        
def save_state(self):
    """Save current tickers to file"""
    try:
        with open(self.state_file, 'w') as f:
            json.dump({
                'tickers': list(self.known_tickers),
                'last_update': datetime.now().isoformat()
            }, f, indent=2)
    except Exception as e:
        print(f"Error saving state: {e}")

def fetch_tickers(self):
    """Fetch ticker symbols from Yahoo Finance API"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(self.api_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        tickers = set()
        
        # Parse Yahoo Finance API response
        if 'finance' in data and 'result' in data['finance']:
            results = data['finance']['result']
            if results and len(results) > 0:
                quotes = results[0].get('quotes', [])
                
                for quote in quotes:
                    symbol = quote.get('symbol', '')
                    # Clean up symbol (remove any suffixes)
                    symbol = symbol.split('.')[0]  # Remove exchange suffixes like .TO
                    
                    if symbol and len(symbol) <= 6 and symbol.replace('-', '').replace('.', '').isalnum():
                        tickers.add(symbol)
                        
        print(f"    Fetched {len(tickers)} day gainers from Yahoo Finance API")
        return tickers
        
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching tickers: {e}")
        return set()
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return set()
    except Exception as e:
        print(f"Error fetching tickers: {e}")
        return set()

def announce(self, message):
    """Announce message via text-to-speech"""
    print(f"🔊 ANNOUNCEMENT: {message}")
    
    if TTS_AVAILABLE:
        try:
            TTS_ENGINE.say(message)
            TTS_ENGINE.runAndWait()
        except Exception as e:
            print(f"TTS Error: {e}")
    else:
        # Fallback: system beep (cross-platform)
        try:
            import subprocess
            import sys
            if sys.platform == "win32":
                import winsound
                winsound.Beep(1000, 1000)  # 1000Hz for 1 second
            elif sys.platform == "darwin":  # macOS
                subprocess.call(['afplay', '/System/Library/Sounds/Glass.aiff'])
            else:  # Linux
                subprocess.call(['paplay', '/usr/share/sounds/alsa/Front_Left.wav'])
        except:
            print("🔔 BEEP! (audio notification failed)")

def check_for_new_tickers(self):
    """Check for new tickers and announce them"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning Yahoo Finance day gainers...")
    current_tickers = self.fetch_tickers()
    
    if not current_tickers:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] No tickers found or fetch failed")
        return
    
    # Find new tickers
    new_tickers = current_tickers - self.known_tickers
    
    if new_tickers:
        ticker_list = ', '.join(sorted(new_tickers))
        message = f"NEW DAY GAINERS DETECTED: {ticker_list}"
        self.announce(message)
        
        # Update known tickers
        self.known_tickers.update(new_tickers)
        self.save_state()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Added {len(new_tickers)} new day gainers: {ticker_list}")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] No new day gainers found. Total tracked: {len(current_tickers)}")

def monitor_loop(self):
    """Main monitoring loop"""
    print(f"🤖 Starting Yahoo Finance Day Gainers Monitor Agent")
    print(f"📍 API: {self.api_url}")
    print(f"⏰ Check interval: {self.check_interval} seconds ({self.check_interval//60} minutes)")
    print(f"🔊 TTS Available: {'Yes' if TTS_AVAILABLE else 'No (install pyttsx3 for audio alerts)'}")
    print(f"📊 Monitoring: Top 25 Day Gainers")
    print("-" * 80)
    
    # Initial check
    self.check_for_new_tickers()
    
    while self.running:
        time.sleep(self.check_interval)
        if self.running:  # Check again in case stop was called during sleep
            self.check_for_new_tickers()

def start(self):
    """Start monitoring in a separate thread"""
    if self.running:
        print("Agent is already running")
        return
        
    self.running = True
    self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
    self.monitor_thread.start()
    print("🚀 Agent started successfully")

def stop(self):
    """Stop monitoring"""
    self.running = False
    if hasattr(self, 'monitor_thread'):
        self.monitor_thread.join(timeout=1)
    print("⏹️ Agent stopped")
```

def main():
“”“Run the ticker monitor agent”””
api_url = “https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=day_gainers&count=25”

```
# Create and start the agent
agent = TickerMonitorAgent(api_url, check_interval=900)  # 15 minutes

try:
    agent.start()
    
    # Keep the main thread alive
    print("Agent is running. Press Ctrl+C to stop...")
    while agent.running:
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\n📍 Stopping agent...")
    agent.stop()
    print("✅ Agent stopped successfully")
```

if **name** == “**main**”:
main()
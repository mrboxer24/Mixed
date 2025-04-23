#!/usr/bin/env python3
"""
0DTE Options Scanner and Trading System

This script identifies and executes trades on 0DTE options with asymmetric risk/reward profiles.
It performs the following functions:
1. Identifies options expiring today across major indices (SPX, SPY, QQQ)
2. Filters contracts by delta values to find potentially profitable setups
3. Calculates risk/reward ratios to find asymmetric opportunities
4. Executes trades with predefined stop loss and take profit levels
5. Monitors positions and automatically closes them when targets are reached

Requirements:
- pandas
- numpy
- yfinance (or a broker API with options data)
- A broker API with options trading capability (TD Ameritrade API used in this example)
"""

import os
import time
import datetime
import pandas as pd
import numpy as np
import yfinance as yf
from tda.auth import easy_client
from tda.client import Client
from tda.orders.equities import equity_buy_market, equity_sell_market
from tda.orders.options import option_buy_to_open_limit, option_sell_to_close_limit
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='0dte_scanner.log'
)
logger = logging.getLogger()

# Configuration parameters - customize these values
CONFIG = {
    "tickers": ["SPY", "QQQ", "SPX"],      # Tickers to scan
    "min_delta": 0.15,                     # Minimum delta
    "max_delta": 0.35,                     # Maximum delta
    "risk_reward_min": 3.0,                # Minimum risk/reward ratio
    "max_loss_percent": 0.50,              # Stop loss (50% of premium)
    "take_profit_percent": 1.50,           # Take profit (150% of premium)
    "max_position_size": 0.05,             # Maximum position size (5% of account)
    "order_type": "LIMIT",                 # Order type (LIMIT or MARKET)
    "limit_price_buffer": 0.05,            # Buffer for limit orders (5%)
    "api_key": "YOUR_TD_AMERITRADE_API_KEY",
    "redirect_uri": "http://localhost:8080",
    "token_path": "td_token.json"
}

class ZeroDTEScanner:
    def __init__(self, config):
        self.config = config
        self.client = self._authenticate_tda()
        self.account_id = self._get_account_id()
        self.positions = []
        
    def _authenticate_tda(self):
        """Authenticate with TD Ameritrade API"""
        try:
            client = easy_client(
                api_key=self.config["api_key"],
                redirect_uri=self.config["redirect_uri"],
                token_path=self.config["token_path"]
            )
            logger.info("Successfully authenticated with TD Ameritrade API")
            return client
        except Exception as e:
            logger.error(f"Failed to authenticate with TD Ameritrade: {e}")
            raise
            
    def _get_account_id(self):
        """Get the primary account ID"""
        try:
            accounts = self.client.get_accounts().json()
            account_id = accounts[0]['securitiesAccount']['accountId']
            logger.info(f"Using account ID: {account_id}")
            return account_id
        except Exception as e:
            logger.error(f"Failed to retrieve account ID: {e}")
            raise
            
    def _get_account_value(self):
        """Get the total account value"""
        try:
            account = self.client.get_account(self.account_id).json()
            account_value = account['securitiesAccount']['currentBalances']['liquidationValue']
            logger.info(f"Current account value: ${account_value}")
            return account_value
        except Exception as e:
            logger.error(f"Failed to retrieve account value: {e}")
            raise

    def get_0dte_options(self, ticker):
        """Get options chains expiring today for a given ticker"""
        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            ticker_obj = yf.Ticker(ticker)
            
            # Get all expiration dates
            expirations = ticker_obj.options
            
            # Find today's expiration if it exists
            today_exp = None
            for exp in expirations:
                exp_date = datetime.datetime.strptime(exp, '%Y-%m-%d').strftime('%Y-%m-%d')
                if exp_date == today:
                    today_exp = exp
                    break
            
            if not today_exp:
                logger.info(f"No 0DTE options available for {ticker} today")
                return pd.DataFrame()
            
            # Get options chain for today
            opt_chain = ticker_obj.option_chain(today_exp)
            
            # Combine calls and puts with a type indicator
            calls = opt_chain.calls
            calls['option_type'] = 'call'
            puts = opt_chain.puts
            puts['option_type'] = 'put'
            
            options = pd.concat([calls, puts])
            
            # Add ticker column
            options['ticker'] = ticker
            
            logger.info(f"Found {len(options)} 0DTE options for {ticker}")
            return options
        
        except Exception as e:
            logger.error(f"Error fetching 0DTE options for {ticker}: {e}")
            return pd.DataFrame()
    
    def filter_by_delta(self, options_df):
        """Filter options by delta range"""
        if options_df.empty:
            return options_df
            
        # For calls, delta is positive; for puts, delta is negative
        # We'll use absolute values for filtering
        options_df['abs_delta'] = options_df['delta'].abs()
        
        filtered = options_df[
            (options_df['abs_delta'] >= self.config['min_delta']) & 
            (options_df['abs_delta'] <= self.config['max_delta'])
        ]
        
        logger.info(f"Filtered to {len(filtered)} options within delta range "
                   f"{self.config['min_delta']}-{self.config['max_delta']}")
        
        return filtered
        
    def calculate_risk_reward(self, options_df):
        """Calculate risk/reward ratio based on option characteristics"""
        if options_df.empty:
            return options_df
            
        # Add risk/reward metrics
        options_df = options_df.copy()
        
        # For each option, estimate risk/reward based on:
        # - Current price vs strike price
        # - Implied volatility
        # - Time decay (theta)
        # - Current premium
        
        # Simple risk/reward calculation:
        # For calls: (strike_price - current_price - premium) / premium
        # For puts: (current_price - strike_price - premium) / premium
        
        results = []
        for _, row in options_df.iterrows():
            underlying_price = row['lastPrice'] * 100 / row['impliedVolatility']  # Rough estimate from IV
            
            if row['option_type'] == 'call':
                # For calls, potential reward is theoretical unlimited
                # But we'll use a reasonable target based on volatility
                potential_reward = row['impliedVolatility'] * underlying_price * 0.1  # 10% of IV * price
                max_loss = row['lastPrice']  # Premium paid
                risk_reward = potential_reward / max_loss if max_loss > 0 else 0
                
            else:  # put
                # For puts, max reward is strike - premium (if goes to zero)
                potential_reward = row['strike'] - row['lastPrice'] if row['strike'] > row['lastPrice'] else 0
                max_loss = row['lastPrice']  # Premium paid
                risk_reward = potential_reward / max_loss if max_loss > 0 else 0
            
            row['risk_reward'] = risk_reward
            results.append(row)
            
        result_df = pd.DataFrame(results)
        
        # Filter by minimum risk/reward ratio
        filtered = result_df[result_df['risk_reward'] >= self.config['risk_reward_min']]
        
        logger.info(f"Found {len(filtered)} options with risk/reward ratio >= {self.config['risk_reward_min']}")
        return filtered
        
    def find_trade_opportunities(self):
        """Find trade opportunities across all tickers"""
        all_opportunities = []
        
        for ticker in self.config['tickers']:
            # Get 0DTE options
            options = self.get_0dte_options(ticker)
            
            if options.empty:
                continue
                
            # Filter by delta
            filtered_options = self.filter_by_delta(options)
            
            if filtered_options.empty:
                continue
                
            # Calculate and filter by risk/reward
            opportunities = self.calculate_risk_reward(filtered_options)
            
            if not opportunities.empty:
                all_opportunities.append(opportunities)
                
        if all_opportunities:
            result = pd.concat(all_opportunities)
            # Sort by risk/reward ratio (descending)
            result = result.sort_values('risk_reward', ascending=False)
            logger.info(f"Found {len(result)} total trade opportunities")
            return result
        else:
            logger.info("No trade opportunities found")
            return pd.DataFrame()
    
    def execute_trade(self, option_data):
        """Execute a trade for a selected option"""
        try:
            account_value = self._get_account_value()
            max_position_value = account_value * self.config["max_position_size"]
            
            # Calculate position size
            contract_price = option_data['lastPrice']
            contract_cost = contract_price * 100  # Each contract is for 100 shares
            max_contracts = int(max_position_value / contract_cost)
            
            if max_contracts < 1:
                logger.warning("Insufficient funds for even one contract")
                return False
                
            # Construct the option symbol in OCC format
            # Example: SPY_MMDDYY[C/P]STRIKE
            expiry = datetime.datetime.now().strftime('%m%d%y')
            option_type = 'C' if option_data['option_type'] == 'call' else 'P'
            strike = f"{option_data['strike']:.1f}"
            
            # Handle whole numbers
            if strike.endswith('.0'):
                strike = strike[:-2]
                
            symbol = f"{option_data['ticker']}_{expiry}{option_type}{strike}"
            
            # Calculate limit price with buffer
            limit_price = option_data['lastPrice'] * (1 + self.config['limit_price_buffer'])
            
            # Place order
            order = option_buy_to_open_limit(symbol, max_contracts, limit_price)
            response = self.client.place_order(self.account_id, order).json()
            
            logger.info(f"Placed order for {max_contracts} contracts of {symbol} at ${limit_price}: {response}")
            
            # Store position information for monitoring
            position = {
                'symbol': symbol,
                'contracts': max_contracts,
                'entry_price': limit_price,
                'stop_loss': limit_price * (1 - self.config['max_loss_percent']),
                'take_profit': limit_price * (1 + self.config['take_profit_percent']),
                'order_id': response['orderId'] if 'orderId' in response else None
            }
            
            self.positions.append(position)
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return False
    
    def monitor_positions(self):
        """Monitor open positions and execute stop loss/take profit orders"""
        if not self.positions:
            return
            
        for position in self.positions[:]:  # Copy the list for safe iteration
            try:
                # Get current option price
                option_quote = self.client.get_quote(position['symbol']).json()
                current_price = option_quote[position['symbol']]['lastPrice']
                
                logger.info(f"Monitoring {position['symbol']}: Current: ${current_price}, "
                           f"Stop: ${position['stop_loss']}, Target: ${position['take_profit']}")
                
                # Check if stop loss or take profit has been reached
                if current_price <= position['stop_loss']:
                    logger.info(f"Stop loss triggered for {position['symbol']}")
                    self._close_position(position, "stop_loss")
                    self.positions.remove(position)
                    
                elif current_price >= position['take_profit']:
                    logger.info(f"Take profit triggered for {position['symbol']}")
                    self._close_position(position, "take_profit")
                    self.positions.remove(position)
                    
            except Exception as e:
                logger.error(f"Error monitoring position {position['symbol']}: {e}")
    
    def _close_position(self, position, reason):
        """Close a position at market price"""
        try:
            # Create sell order
            order = option_sell_to_close_limit(
                position['symbol'], 
                position['contracts'], 
                0.01  # Use a very low price for a market-like sell
            )
            
            response = self.client.place_order(self.account_id, order).json()
            
            logger.info(f"Closed position {position['symbol']} due to {reason}: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Error closing position {position['symbol']}: {e}")
            return False
    
    def run(self):
        """Main execution loop"""
        logger.info("Starting 0DTE scanner and trader")
        
        try:
            # Find trade opportunities
            opportunities = self.find_trade_opportunities()
            
            if not opportunities.empty:
                # Take the top opportunity
                best_opportunity = opportunities.iloc[0]
                logger.info(f"Best opportunity: {best_opportunity['ticker']} {best_opportunity['option_type']} "
                           f"${best_opportunity['strike']} with risk/reward ratio {best_opportunity['risk_reward']:.2f}")
                
                # Execute the trade
                success = self.execute_trade(best_opportunity)
                
                if success:
                    logger.info("Trade executed successfully")
                else:
                    logger.error("Failed to execute trade")
            
            # Enter monitoring loop
            while self.positions:
                self.monitor_positions()
                time.sleep(5)  # Check every 5 seconds
                
            logger.info("All positions closed, scanner complete")
            
        except Exception as e:
            logger.error(f"Error in scanner main loop: {e}")

if __name__ == "__main__":
    scanner = ZeroDTEScanner(CONFIG)
    scanner.run()
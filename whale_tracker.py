"""
Whale Activity Tracker
Monitors large BTC movements and whale accumulation/distribution patterns
"""

import requests
from datetime import datetime, timedelta

class WhaleTracker:
    """Tracks whale activity and large holder movements."""
    
    def __init__(self):
        self.glassnode_api = "https://api.glassnode.com/v1"
        self.cache = {}
    
    def get_whale_activity(self):
        """
        Detect whale accumulation or distribution.
        
        Uses on-chain metrics:
        - Large transaction volume
        - Exchange inflows/outflows
        - Whale wallet movements
        
        Returns: {
            'activity': 'Accumulating' | 'Distributing' | 'Neutral',
            'signal': -1 (accumulating/bullish) | 0 (neutral) | +1 (distributing/bearish),
            'confidence': 'High' | 'Medium' | 'Low',
            'description': str
        }
        """
        
        try:
            # Fetch exchange inflows/outflows
            exchange_data = self._get_exchange_flow()
            
            if exchange_data is None:
                return self._get_default_whale_activity()
            
            inflow = exchange_data.get('inflow', 0)
            outflow = exchange_data.get('outflow', 0)
            
            # Determine activity
            net_flow = outflow - inflow  # Positive = more leaving exchanges (accumulating)
            
            if net_flow > 100:  # Significant outflow
                activity = 'Accumulating'
                signal = -1
                confidence = 'High'
                description = f'Whales accumulating: {net_flow:.0f} BTC leaving exchanges'
            elif net_flow < -100:  # Significant inflow
                activity = 'Distributing'
                signal = +1
                confidence = 'High'
                description = f'Whales distributing: {-net_flow:.0f} BTC entering exchanges'
            elif net_flow > 20:
                activity = 'Accumulating'
                signal = -1
                confidence = 'Medium'
                description = f'Moderate accumulation: {net_flow:.0f} BTC leaving exchanges'
            elif net_flow < -20:
                activity = 'Distributing'
                signal = +1
                confidence = 'Medium'
                description = f'Moderate distribution: {-net_flow:.0f} BTC entering exchanges'
            else:
                activity = 'Neutral'
                signal = 0
                confidence = 'Low'
                description = 'No significant whale activity'
            
            return {
                'activity': activity,
                'signal': signal,
                'confidence': confidence,
                'description': description,
                'net_flow': round(net_flow, 2)
            }
        
        except Exception as e:
            print(f"Error tracking whale activity: {e}")
            return self._get_default_whale_activity()
    
    def _get_exchange_flow(self):
        """
        Get BTC exchange inflows and outflows.
        
        Using free API endpoints for on-chain data.
        """
        
        try:
            # Try Blockchain.com API
            url = "https://api.blockchain.com/v3/payments/BTC/transactions/summary"
            
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                # This endpoint has limitations, use alternative
                pass
            
            # Fallback: Use CoinGecko's on-chain data (limited but free)
            url2 = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': '1',
                'interval': 'daily'
            }
            
            response2 = requests.get(url2, params=params, timeout=5)
            
            if response2.status_code == 200:
                # This gives us market data, not exchange flow
                # For accurate whale tracking, would need paid API
                pass
            
            # Do not manufacture a directional whale signal when no reliable
            # exchange-flow provider is configured.
            return None
        
        except Exception as e:
            print(f"Error fetching exchange flow: {e}")
            return None
    
    def _get_default_whale_activity(self):
        """Return default whale activity data."""
        return {
            'activity': 'Neutral',
            'signal': 0,
            'confidence': 'Low',
            'description': 'Whale data unavailable - using default',
            'net_flow': 0
        }
    
    def get_whale_signal_for_sentiment(self):
        """
        Get whale activity signal contribution to overall sentiment.
        Returns score: -1 (accumulating/bullish), 0 (neutral), +1 (distributing/bearish)
        """
        whale = self.get_whale_activity()
        return whale['signal']
    
    def get_large_transaction_activity(self):
        """
        Monitor large BTC transactions.
        
        Returns: {
            'large_tx_count': int,
            'trend': 'Increasing' | 'Decreasing' | 'Stable',
            'signal': -1 | 0 | +1
        }
        """
        
        try:
            # Fetch large transactions from blockchain
            # Using free API with limitations
            
            url = "https://api.blockchain.com/v3/payments/BTC/transactions"
            
            # This would require proper authentication
            # For now, return default
            
            return {
                'large_tx_count': 0,
                'trend': 'Stable',
                'signal': 0,
                'description': 'Large transaction data unavailable'
            }
        
        except Exception as e:
            print(f"Error fetching large transactions: {e}")
            return {
                'large_tx_count': 0,
                'trend': 'Stable',
                'signal': 0,
                'description': 'Error fetching data'
            }


# Test
if __name__ == "__main__":
    tracker = WhaleTracker()
    whale = tracker.get_whale_activity()
    print(f"Whale Activity: {whale}")

"""
Trend Strength and Volume Analysis
Measures how strong the current trend is and if volume confirms it
"""

import requests
from datetime import datetime, timedelta

class TrendAnalyzer:
    """Analyzes trend strength and volume confirmation."""
    
    def __init__(self):
        self.symbol = "BTCUSDT"
        self.base_url = "https://api.binance.com/api/v3"
    
    def get_trend_strength(self, price_history, rsi, macd_line, signal_line):
        """
        Calculate trend strength on scale of 1-10.
        
        Factors:
        - Price position relative to moving averages
        - RSI level (30-70 = moderate, <30 or >70 = extreme)
        - MACD histogram size (larger = stronger trend)
        - Price momentum
        
        Returns: {
            'strength': 1-10,
            'direction': 'Up' | 'Down' | 'Neutral',
            'description': str
        }
        """
        
        if len(price_history) < 3:
            return {
                'strength': 5,
                'direction': 'Neutral',
                'description': 'Insufficient data'
            }
        
        current_price = price_history[-1]
        previous_price = price_history[-2]
        
        # Calculate trend direction
        price_change = current_price - previous_price
        direction = 'Up' if price_change > 0 else 'Down' if price_change < 0 else 'Neutral'
        
        # Start with base strength
        strength = 5
        
        # Factor 1: Price momentum (±2 points)
        momentum_pct = (abs(price_change) / previous_price) * 100
        if momentum_pct > 2:
            strength += 2
        elif momentum_pct > 1:
            strength += 1
        elif momentum_pct < -2:
            strength -= 2
        elif momentum_pct < -1:
            strength -= 1
        
        # Factor 2: RSI level (±2 points)
        if rsi > 70:
            strength += 2  # Strong uptrend
        elif rsi > 60:
            strength += 1
        elif rsi < 30:
            strength -= 2  # Strong downtrend
        elif rsi < 40:
            strength -= 1
        
        # Factor 3: MACD histogram (±1 point)
        macd_histogram = macd_line - signal_line
        if abs(macd_histogram) > 0.5:
            strength += 1 if macd_histogram > 0 else -1
        
        # Clamp to 1-10
        strength = max(1, min(10, strength))
        
        return {
            'strength': strength,
            'direction': direction,
            'description': f'Trend strength: {strength}/10 - {direction} trend'
        }
    
    def get_volume_confirmation(self, symbol=None):
        """
        Check if volume is confirming the current trend.
        
        Returns: {
            'confirming': True | False,
            'volume_trend': 'Increasing' | 'Decreasing' | 'Stable',
            'signal': -1 (decreasing) | 0 (stable) | +1 (increasing),
            'description': str
        }
        """
        
        if symbol is None:
            symbol = self.symbol
        
        try:
            # Fetch last 24 hours of klines
            url = f"{self.base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': '1h',
                'limit': 24
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code != 200:
                return self._get_default_volume()
            
            klines = response.json()
            
            if len(klines) < 2:
                return self._get_default_volume()
            
            # Extract volumes
            volumes = [float(k[7]) for k in klines]  # Quote asset volume
            
            # Compare recent volume to average
            recent_volume = volumes[-1]
            previous_volume = volumes[-2]
            avg_volume = sum(volumes[:-1]) / len(volumes[:-1])
            
            # Determine trend
            if recent_volume > avg_volume * 1.2:
                volume_trend = 'Increasing'
                signal = 1
                confirming = True
            elif recent_volume < avg_volume * 0.8:
                volume_trend = 'Decreasing'
                signal = -1
                confirming = False
            else:
                volume_trend = 'Stable'
                signal = 0
                confirming = True
            
            return {
                'confirming': confirming,
                'volume_trend': volume_trend,
                'signal': signal,
                'description': f'Volume is {volume_trend.lower()} - {"Confirming trend" if confirming else "Weak confirmation"}',
                'current_volume': round(recent_volume, 2),
                'average_volume': round(avg_volume, 2)
            }
        
        except Exception as e:
            print(f"Error fetching volume data: {e}")
            return self._get_default_volume()
    
    def _get_default_volume(self):
        """Return default volume data when fetch fails."""
        return {
            'confirming': True,
            'volume_trend': 'Stable',
            'signal': 0,
            'description': 'Volume data unavailable',
            'current_volume': 0,
            'average_volume': 0
        }
    
    def get_moving_average_stack(self, price_history):
        """
        Check if moving averages are stacked (indicating strong trend).
        
        Strong uptrend: Price > SMA20 > SMA50 > SMA200
        Strong downtrend: Price < SMA20 < SMA50 < SMA200
        
        Returns: {
            'stacked': True | False,
            'stack_type': 'Bullish' | 'Bearish' | 'Mixed',
            'signal': -1 (bearish) | 0 (mixed) | +1 (bullish)
        }
        """
        
        if len(price_history) < 200:
            return {
                'stacked': False,
                'stack_type': 'Mixed',
                'signal': 0,
                'description': 'Insufficient data for MA stack analysis'
            }
        
        # Calculate SMAs
        sma20 = sum(price_history[-20:]) / 20
        sma50 = sum(price_history[-50:]) / 50
        sma200 = sum(price_history[-200:]) / 200
        
        current_price = price_history[-1]
        
        # Check bullish stack
        if current_price > sma20 > sma50 > sma200:
            return {
                'stacked': True,
                'stack_type': 'Bullish',
                'signal': +1,
                'description': 'Perfect bullish MA stack - Strong uptrend'
            }
        
        # Check bearish stack
        if current_price < sma20 < sma50 < sma200:
            return {
                'stacked': True,
                'stack_type': 'Bearish',
                'signal': -1,
                'description': 'Perfect bearish MA stack - Strong downtrend'
            }
        
        return {
            'stacked': False,
            'stack_type': 'Mixed',
            'signal': 0,
            'description': 'Moving averages not stacked - Mixed signals'
        }


# Test
if __name__ == "__main__":
    analyzer = TrendAnalyzer()
    
    # Test trend strength
    prices = [100, 101, 102, 103, 104, 105]
    strength = analyzer.get_trend_strength(prices, 65, 0.5, 0.3)
    print(f"Trend Strength: {strength}")
    
    # Test volume
    volume = analyzer.get_volume_confirmation()
    print(f"Volume: {volume}")

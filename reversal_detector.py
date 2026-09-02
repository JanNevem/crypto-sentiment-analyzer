"""
Early Reversal Detection
Detects RSI and MACD divergences that signal potential reversals
"""

import json
import os
from datetime import datetime

class ReversalDetector:
    """Detects early reversal signals through divergence analysis."""
    
    def __init__(self):
        self.history_file = "reversal_history.json"
        self.history = self._load_history()
    
    def _load_history(self):
        """Load historical price and indicator data."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except:
                return {'prices': [], 'rsi': [], 'macd': []}
        return {'prices': [], 'rsi': [], 'macd': []}
    
    def _save_history(self):
        """Save historical data."""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f)
    
    def detect_rsi_divergence(self, current_price, current_rsi, price_history, rsi_history):
        """
        Detect RSI divergence.
        
        Bullish Divergence: Price makes lower low, but RSI makes higher low
        Bearish Divergence: Price makes higher high, but RSI makes lower high
        
        Returns: {
            'type': 'Bullish' | 'Bearish' | 'None',
            'strength': 'Strong' | 'Moderate' | 'Weak',
            'signal': -1 (bullish) | 0 (none) | +1 (bearish),
            'description': str
        }
        """
        
        if len(price_history) < 3 or len(rsi_history) < 3:
            return {
                'type': 'None',
                'strength': 'None',
                'signal': 0,
                'description': 'Insufficient data'
            }
        
        # Get recent pivots (last 3 candles)
        recent_prices = price_history[-3:]
        recent_rsi = rsi_history[-3:]
        
        # Find local highs and lows
        price_prev_low = min(recent_prices[:-1])
        price_current_low = recent_prices[-1]
        
        price_prev_high = max(recent_prices[:-1])
        price_current_high = recent_prices[-1]
        
        rsi_prev_low = min(recent_rsi[:-1])
        rsi_current_low = recent_rsi[-1]
        
        rsi_prev_high = max(recent_rsi[:-1])
        rsi_current_high = recent_rsi[-1]
        
        # Bullish Divergence: Price lower low, RSI higher low
        if price_current_low < price_prev_low and rsi_current_low > rsi_prev_low:
            strength = 'Strong' if (rsi_current_low - rsi_prev_low) > 10 else 'Moderate'
            return {
                'type': 'Bullish',
                'strength': strength,
                'signal': -1,
                'description': f'Price made lower low but RSI made higher low - Bullish reversal likely'
            }
        
        # Bearish Divergence: Price higher high, RSI lower high
        if price_current_high > price_prev_high and rsi_current_high < rsi_prev_high:
            strength = 'Strong' if (rsi_prev_high - rsi_current_high) > 10 else 'Moderate'
            return {
                'type': 'Bearish',
                'strength': strength,
                'signal': +1,
                'description': f'Price made higher high but RSI made lower high - Bearish reversal likely'
            }
        
        return {
            'type': 'None',
            'strength': 'None',
            'signal': 0,
            'description': 'No divergence detected'
        }
    
    def detect_macd_divergence(self, macd_line, signal_line, macd_history):
        """
        Detect MACD divergence.
        
        Histogram shrinking while price extends = Momentum dying
        
        Returns: {
            'type': 'Bullish' | 'Bearish' | 'None',
            'strength': 'Strong' | 'Moderate' | 'Weak',
            'signal': -1 (bullish) | 0 (none) | +1 (bearish),
            'description': str
        }
        """
        
        if len(macd_history) < 3:
            return {
                'type': 'None',
                'strength': 'None',
                'signal': 0,
                'description': 'Insufficient MACD data'
            }
        
        # Calculate histogram (MACD - Signal)
        current_histogram = macd_line - signal_line
        previous_histogram = macd_history[-2] if len(macd_history) > 1 else current_histogram
        
        # Check if histogram is shrinking
        histogram_shrinking = abs(current_histogram) < abs(previous_histogram)
        
        if histogram_shrinking:
            if current_histogram > 0:
                # Bullish histogram shrinking = Bullish momentum dying
                return {
                    'type': 'Bearish',
                    'strength': 'Moderate',
                    'signal': +1,
                    'description': 'MACD histogram shrinking - Bullish momentum weakening'
                }
            else:
                # Bearish histogram shrinking = Bearish momentum dying
                return {
                    'type': 'Bullish',
                    'strength': 'Moderate',
                    'signal': -1,
                    'description': 'MACD histogram shrinking - Bearish momentum weakening'
                }
        
        return {
            'type': 'None',
            'strength': 'None',
            'signal': 0,
            'description': 'MACD histogram stable or growing'
        }
    
    def get_reversal_signals(self, current_price, current_rsi, price_history, rsi_history, 
                            macd_line, signal_line, macd_history):
        """
        Get all reversal signals.
        
        Returns: {
            'rsi_divergence': {...},
            'macd_divergence': {...},
            'overall_signal': -1 | 0 | +1,
            'has_reversal_warning': bool
        }
        """
        
        rsi_div = self.detect_rsi_divergence(current_price, current_rsi, price_history, rsi_history)
        macd_div = self.detect_macd_divergence(macd_line, signal_line, macd_history)
        
        # Combine signals
        overall_signal = 0
        if rsi_div['signal'] != 0:
            overall_signal += rsi_div['signal']
        if macd_div['signal'] != 0:
            overall_signal += macd_div['signal']
        
        # Clamp to -1, 0, +1
        if overall_signal > 0:
            overall_signal = 1
        elif overall_signal < 0:
            overall_signal = -1
        
        has_warning = rsi_div['type'] != 'None' or macd_div['type'] != 'None'
        
        return {
            'rsi_divergence': rsi_div,
            'macd_divergence': macd_div,
            'overall_signal': overall_signal,
            'has_reversal_warning': has_warning
        }


# Test
if __name__ == "__main__":
    detector = ReversalDetector()
    
    # Test data
    prices = [100, 102, 101, 103, 102, 104]
    rsi = [50, 55, 52, 60, 58, 65]
    
    result = detector.detect_rsi_divergence(104, 65, prices, rsi)
    print(f"RSI Divergence: {result}")

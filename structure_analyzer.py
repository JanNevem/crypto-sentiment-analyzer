"""
Market Structure Analyzer - Phase 3 Advanced Indicator
Detects swing highs/lows and break of structure (BoS) signals
"""

import requests
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class StructureAnalyzer:
    """Analyze market structure for swing highs/lows and BoS signals."""
    
    def __init__(self):
        self.last_update = None
        self.structure_data = {}
    
    def get_market_structure(self) -> Dict:
        """
        Analyze market structure from recent price action.
        
        Returns:
            Dict with structure analysis and -2 to +2 score
        """
        try:
            # Fetch recent 4-hour candles for structure analysis
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': '4h',
                'limit': 50  # Get last 50 4-hour candles
            }
            
            response = requests.get(url, params=params, timeout=10)
            klines = response.json()
            
            if not klines or len(klines) < 5:
                return {
                    'structure': 'Insufficient Data',
                    'swing_high': 0,
                    'swing_low': 0,
                    'current_price': 0,
                    'higher_highs': False,
                    'higher_lows': False,
                    'lower_highs': False,
                    'lower_lows': False,
                    'break_of_structure': False,
                    'bos_direction': 'None',
                    'signal': 0,
                    'confidence': 'Low'
                }
            
            # Extract closes and highs/lows
            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            current_price = closes[-1]
            
            # Find swing highs and lows (last 10 candles)
            recent_closes = closes[-10:]
            recent_highs = highs[-10:]
            recent_lows = lows[-10:]
            
            # Identify swing high (higher than neighbors)
            swing_high = max(recent_highs)
            swing_high_idx = recent_highs.index(swing_high)
            
            # Identify swing low (lower than neighbors)
            swing_low = min(recent_lows)
            swing_low_idx = recent_lows.index(swing_low)
            
            # Analyze trend structure
            higher_highs = False
            higher_lows = False
            lower_highs = False
            lower_lows = False
            
            if len(closes) >= 5:
                # Check for higher highs (uptrend)
                if highs[-1] > highs[-3] and highs[-3] > highs[-5]:
                    higher_highs = True
                
                # Check for higher lows (uptrend)
                if lows[-1] > lows[-3] and lows[-3] > lows[-5]:
                    higher_lows = True
                
                # Check for lower highs (downtrend)
                if highs[-1] < highs[-3] and highs[-3] < highs[-5]:
                    lower_highs = True
                
                # Check for lower lows (downtrend)
                if lows[-1] < lows[-3] and lows[-3] < lows[-5]:
                    lower_lows = True
            
            # Detect break of structure
            break_of_structure = False
            bos_direction = "None"
            
            # Bullish BoS: Price breaks above previous swing high
            if current_price > swing_high and swing_high_idx < 5:
                break_of_structure = True
                bos_direction = "Bullish BoS"
            
            # Bearish BoS: Price breaks below previous swing low
            if current_price < swing_low and swing_low_idx < 5:
                break_of_structure = True
                bos_direction = "Bearish BoS"
            
            # Determine structure and signal
            if higher_highs and higher_lows:
                structure = "Uptrend"
                if break_of_structure and bos_direction == "Bullish BoS":
                    signal = 2  # Ultra bullish
                    confidence = "High"
                else:
                    signal = 1  # Bullish
                    confidence = "Medium"
            
            elif lower_highs and lower_lows:
                structure = "Downtrend"
                if break_of_structure and bos_direction == "Bearish BoS":
                    signal = -2  # Ultra bearish
                    confidence = "High"
                else:
                    signal = -1  # Bearish
                    confidence = "Medium"
            
            else:
                structure = "Consolidation"
                signal = 0
                confidence = "Low"
            
            self.structure_data = {
                'structure': structure,
                'swing_high': swing_high,
                'swing_low': swing_low,
                'current_price': current_price,
                'higher_highs': higher_highs,
                'higher_lows': higher_lows,
                'lower_highs': lower_highs,
                'lower_lows': lower_lows,
                'break_of_structure': break_of_structure,
                'bos_direction': bos_direction,
                'signal': signal,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat()
            }
            
            return self.structure_data
        
        except Exception as e:
            print(f"Error analyzing market structure: {e}")
            return {
                'structure': 'Error',
                'swing_high': 0,
                'swing_low': 0,
                'current_price': 0,
                'higher_highs': False,
                'higher_lows': False,
                'lower_highs': False,
                'lower_lows': False,
                'break_of_structure': False,
                'bos_direction': 'None',
                'signal': 0,
                'confidence': 'Low'
            }
    
    def get_structure_analysis(self) -> Dict:
        """Get current market structure analysis."""
        return self.get_market_structure()
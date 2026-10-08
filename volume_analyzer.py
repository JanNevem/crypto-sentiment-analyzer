"""
Volume Profile Analyzer - Phase 4 Advanced Indicator
Analyzes volume trends and detects volume spikes
"""

import requests
import numpy as np
from datetime import datetime, timedelta
from typing import Dict

class VolumeAnalyzer:
    """Analyze volume profile and detect volume-based signals."""
    
    def __init__(self):
        self.last_update = None
        self.volume_data = {}
    
    def get_volume_profile(self) -> Dict:
        """
        Analyze volume profile from recent price action.
        
        Returns:
            Dict with volume analysis and -2 to +2 score
        """
        try:
            # Fetch recent daily candles for volume analysis
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': '1d',
                'limit': 30  # Get last 30 days
            }
            
            response = requests.get(url, params=params, timeout=10)
            klines = response.json()
            
            if not klines or len(klines) < 5:
                return {
                    'volume_trend': 'Insufficient Data',
                    'current_volume': 0,
                    'avg_volume': 0,
                    'volume_spike': False,
                    'volume_increasing': False,
                    'on_balance_volume': 0,
                    'obv_trend': 'Neutral',
                    'signal': 0,
                    'confidence': 'Low'
                }
            
            # Extract volume and price data
            closes = [float(k[4]) for k in klines]
            volumes = [float(k[7]) for k in klines]  # Quote asset volume
            
            current_volume = volumes[-1]
            avg_volume = np.mean(volumes[-20:])  # Average of last 20 days
            
            # Detect volume spike (current volume > 1.5x average)
            volume_spike = current_volume > avg_volume * 1.5
            
            # Check if volume is increasing (trend)
            volume_increasing = current_volume > avg_volume
            
            # Calculate On-Balance Volume (OBV)
            obv = 0
            for i in range(len(closes)):
                if i == 0:
                    obv = 0
                else:
                    if closes[i] > closes[i-1]:
                        obv += volumes[i]
                    elif closes[i] < closes[i-1]:
                        obv -= volumes[i]
            
            # Determine OBV trend
            obv_values = []
            obv_temp = 0
            for i in range(len(closes)):
                if i == 0:
                    obv_temp = 0
                else:
                    if closes[i] > closes[i-1]:
                        obv_temp += volumes[i]
                    elif closes[i] < closes[i-1]:
                        obv_temp -= volumes[i]
                obv_values.append(obv_temp)
            
            # OBV trend: increasing or decreasing
            if len(obv_values) >= 5:
                obv_delta = obv_values[-1] - obv_values[-5]
                obv_trend_direction = obv_delta > 0
                obv_trend_bearish = obv_delta < 0
            else:
                obv_trend_direction = False
                obv_trend_bearish = False

            obv_trend = "Increasing" if obv_trend_direction else "Decreasing" if obv_trend_bearish else "Neutral"
            
            # Determine signal
            if volume_spike and volume_increasing:
                if closes[-1] > closes[-2]:
                    # Volume spike on up move = bullish
                    signal = 2
                    volume_trend = "Strong Buying"
                    confidence = "High"
                else:
                    # Volume spike on down move = bearish
                    signal = -2
                    volume_trend = "Strong Selling"
                    confidence = "High"
            
            elif volume_increasing:
                if closes[-1] > closes[-2]:
                    signal = 1
                    volume_trend = "Increasing Volume (Up)"
                    confidence = "Medium"
                else:
                    signal = -1
                    volume_trend = "Increasing Volume (Down)"
                    confidence = "Medium"
            
            elif obv_trend_direction:
                signal = 1
                volume_trend = "OBV Increasing"
                confidence = "Medium"

            elif obv_trend_bearish:
                signal = -1
                volume_trend = "OBV Decreasing"
                confidence = "Medium"
            
            else:
                signal = 0
                volume_trend = "Normal/Decreasing"
                confidence = "Low"
            
            self.volume_data = {
                'volume_trend': volume_trend,
                'current_volume': current_volume,
                'avg_volume': avg_volume,
                'volume_spike': volume_spike,
                'volume_increasing': volume_increasing,
                'on_balance_volume': obv,
                'obv_trend': obv_trend,
                'signal': signal,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat()
            }
            
            return self.volume_data
        
        except Exception as e:
            print(f"Error analyzing volume profile: {e}")
            return {
                'volume_trend': 'Error',
                'current_volume': 0,
                'avg_volume': 0,
                'volume_spike': False,
                'volume_increasing': False,
                'on_balance_volume': 0,
                'obv_trend': 'Neutral',
                'signal': 0,
                'confidence': 'Low'
            }
    
    def get_volume_analysis(self) -> Dict:
        """Get current volume profile analysis."""
        return self.get_volume_profile()

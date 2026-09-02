f"""
Enhanced Crypto Market Sentiment Analyzer - Phase 3
12 indicators split into Early Reversal + Confirmatory
With Signal Generation (Scout/Core/Max)
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, List
import json
import os

# Import Phase 2 modules
from reversal_detector import ReversalDetector
from trend_analyzer import TrendAnalyzer
from whale_tracker import WhaleTracker
from structure_analyzer import StructureAnalyzer
from volume_analyzer import VolumeAnalyzer
from signal_generator import SignalGenerator
from dollar_strength_analyzer import DollarStrengthAnalyzer


class SentimentAnalyzer:
    """Sentiment analyzer with 12 indicators and signal generation."""
    
    def __init__(self):
        self.current_sentiment = None
        self.previous_sentiment = None
        self.last_update = None
        self.indicator_scores = {}
        self.early_reversal_scores = {}
        self.confirmatory_scores = {}
        
        # Initialize analyzers
        self.reversal_detector = ReversalDetector()
        self.trend_analyzer = TrendAnalyzer()
        self.whale_tracker = WhaleTracker()
        self.structure_analyzer = StructureAnalyzer()
        self.volume_analyzer = VolumeAnalyzer()
        self.signal_generator = SignalGenerator()
        self.dollar_strength_analyzer = DollarStrengthAnalyzer()
        
        # Store price history for analysis
        self.price_history = []
        self.rsi_history = []
        self.macd_history = []
    
    # ==================== EARLY REVERSAL INDICATORS ====================
    # (Leading indicators - predict change)
    
    def get_rsi_divergence(self) -> Dict:
        """[EARLY] RSI Divergence - Leading indicator"""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': '1w',
                'limit': 14
            }
            
            response = requests.get(url, params=params, timeout=5)
            klines = response.json()
            closes = [float(k[4]) for k in klines]
            
            # Calculate RSI
            deltas = np.diff(closes)
            seed = deltas[:14]
            up = seed[seed >= 0].sum() / 14
            down = -seed[seed < 0].sum() / 14
            rs = up / down if down != 0 else 0
            rsi = 100 - (100 / (1 + rs))
            
            self.rsi_history = closes
            
            # Detect divergence
            if len(closes) >= 3:
                price_higher = closes[-1] > closes[-2]
                rsi_lower = rsi < 50
                
                if price_higher and rsi_lower:
                    return {'type': 'Bullish Divergence', 'signal': 2}
                elif not price_higher and rsi > 50:
                    return {'type': 'Bearish Divergence', 'signal': -2}
            
            return {'type': 'None', 'signal': 0}
        except Exception as e:
            print(f"Error in RSI Divergence: {e}")
            return {'type': 'None', 'signal': 0}
    
    def get_macd_divergence(self) -> Dict:
        """[EARLY] MACD Divergence - Leading indicator"""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': '1d',
                'limit': 26
            }
            
            response = requests.get(url, params=params, timeout=5)
            klines = response.json()
            closes = [float(k[4]) for k in klines]
            
            # Calculate MACD
            ema12 = pd.Series(closes).ewm(span=12).mean().iloc[-1]
            ema26 = pd.Series(closes).ewm(span=26).mean().iloc[-1]
            macd_line = ema12 - ema26
            
            self.macd_history.append(macd_line)
            self.price_history = closes
            
            if macd_line > 0:
                return {'type': 'Bullish', 'signal': 1}
            else:
                return {'type': 'Bearish', 'signal': -1}
        except Exception as e:
            print(f"Error in MACD Divergence: {e}")
            return {'type': 'None', 'signal': 0}
    
    def get_whale_accumulation(self) -> Dict:
        """[EARLY] Whale Activity - Leading indicator"""
        return self.whale_tracker.get_whale_activity()
    
    def get_structure_break(self) -> Dict:
        """[EARLY] Break of Structure - Leading indicator"""
        return self.structure_analyzer.get_structure_analysis()
    
    # ==================== CONFIRMATORY INDICATORS ====================
    # (Lagging indicators - confirm change)
    
    def get_fear_greed_index(self) -> Tuple[int, str]:
        """[CONFIRM] Fetch Crypto Fear & Greed Index"""
        try:
            response = requests.get(
                "https://api.alternative.me/fng/?limit=1",
                timeout=10
            )
            data = response.json()
            value = int(data['data'][0]['value'])
            
            if value < 25:
                sentiment = "Extreme Fear"
            elif value < 45:
                sentiment = "Fear"
            elif value < 55:
                sentiment = "Neutral"
            elif value < 75:
                sentiment = "Greed"
            else:
                sentiment = "Extreme Greed"
                
            return value, sentiment
        except Exception as e:
            print(f"Error fetching Fear & Greed Index: {e}")
            return 50, "Neutral"
    
    def get_trend_strength(self) -> Dict:
        """[CONFIRM] Get trend strength meter"""
        if len(self.price_history) < 3:
            return {'strength': 5, 'direction': 'Neutral', 'description': 'Insufficient data'}
        
        rsi_value = 50
        macd_line = self.macd_history[-1] if self.macd_history else 0
        signal_line = 0
        
        return self.trend_analyzer.get_trend_strength(
            self.price_history, rsi_value, macd_line, signal_line
        )
    
    def get_volume_confirmation(self) -> Dict:
        """[CONFIRM] Get volume analysis"""
        return self.trend_analyzer.get_volume_confirmation()
    
    def get_bollinger_bands(self) -> str:
        """[CONFIRM] Calculate Bollinger Bands"""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': '1d',
                'limit': 20
            }
            
            response = requests.get(url, params=params, timeout=5)
            klines = response.json()
            
            closes = [float(k[4]) for k in klines]
            current_price = closes[-1]
            
            sma = np.mean(closes)
            std = np.std(closes)
            upper_band = sma + (std * 2)
            lower_band = sma - (std * 2)
            
            if current_price > upper_band:
                return "Breakout Up"
            elif current_price < lower_band:
                return "Breakout Down"
            else:
                return "Normal"
        except Exception as e:
            print(f"Error calculating Bollinger Bands: {e}")
            return "Normal"
    
    def get_dollar_strength(self) -> Dict:
        """[CONFIRM] Get broad-dollar strength and its BTC sentiment score."""
        return self.dollar_strength_analyzer.get_dollar_strength()

    def get_volume_profile(self) -> Dict:
        """[CONFIRM] Get volume profile analysis"""
        return self.volume_analyzer.get_volume_analysis()
    
    def get_open_interest_trend(self) -> str:
        """[CONFIRM] Fetch Open Interest trend"""
        try:
            url = "https://fapi.binance.com/fapi/v1/openInterest"
            params = {'symbol': 'BTCUSDT'}
            
            response = requests.get(url, params=params, timeout=5)
            current_oi = float(response.json()['openInterest'])
            
            cache_file = "oi_cache.json"
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    previous_oi = cache.get('last_oi', current_oi)
            else:
                previous_oi = current_oi
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'last_oi': current_oi}, f)
            
            if current_oi > previous_oi * 1.05:
                return "Increasing"
            elif current_oi < previous_oi * 0.95:
                return "Decreasing"
            else:
                return "Stable"
        except Exception as e:
            print(f"Error fetching Open Interest: {e}")
            return "Stable"
    
    def get_funding_rate(self) -> str:
        """[CONFIRM] Fetch current funding rate"""
        try:
            url = "https://fapi.binance.com/fapi/v1/fundingRate"
            params = {'symbol': 'BTCUSDT', 'limit': 1}
            
            response = requests.get(url, params=params, timeout=5)
            rate = float(response.json()[0]['fundingRate'])
            
            if rate > 0.0005:
                return "Positive"
            elif rate < -0.0005:
                return "Negative"
            else:
                return "Neutral"
        except Exception as e:
            print(f"Error fetching Funding Rate: {e}")
            return "Neutral"
    
    # ==================== SCORING CONVERSION ====================
    
    def _convert_to_score(self, value: int, signal: str, indicator_type: str) -> int:
        """Convert indicator signals to -2 to +2 score."""
        
        if indicator_type == "fear_greed":
            if signal == "Extreme Greed":
                return 2
            elif signal == "Greed":
                return 1
            elif signal == "Neutral":
                return 0
            elif signal == "Fear":
                return -1
            elif signal == "Extreme Fear":
                return -2
        
        elif indicator_type == "bollinger":
            if signal == "Breakout Up":
                return 2
            elif signal == "Breakout Down":
                return -2
            else:
                return 0
        
        elif indicator_type == "oi":
            if signal == "Increasing":
                return 1
            elif signal == "Decreasing":
                return -1
            else:
                return 0
        
        elif indicator_type == "funding":
            if signal == "Positive":
                return 1
            elif signal == "Negative":
                return -1
            else:
                return 0
        
        return 0
    
    # ==================== MAIN ANALYSIS ====================
    
    def analyze_sentiment(self) -> Dict:
        """Analyze all 12 indicators split into two sections."""
        
        print("\n" + "="*70)
        print(f"ANALYZING SENTIMENT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # EARLY REVERSAL INDICATORS (Leading - predict change)
        print("\n[EARLY REVERSAL INDICATORS - Leading Signals]")
        
        print("[1/11] RSI Divergence...")
        rsi_div = self.get_rsi_divergence()
        rsi_div_score = rsi_div['signal']
        print(f"      RSI Divergence: {rsi_div['type']} -> Score: {rsi_div_score:+d}")
        
        print("[2/11] MACD Divergence...")
        macd_div = self.get_macd_divergence()
        macd_div_score = macd_div['signal']
        print(f"      MACD Divergence: {macd_div['type']} -> Score: {macd_div_score:+d}")
        
        print("[3/11] Whale Accumulation...")
        whale = self.get_whale_accumulation()
        whale_score = whale['signal']
        print(f"      Whales: {whale['activity']} -> Score: {whale_score:+d}")
        
        print("[4/11] Break of Structure...")
        structure = self.get_structure_break()
        structure_score = structure['signal']
        print(f"      Structure: {structure['structure']} -> Score: {structure_score:+d}")
        
        early_reversal_total = rsi_div_score + macd_div_score + whale_score + structure_score
        
        # CONFIRMATORY INDICATORS (Lagging - confirm change)
        print("\n[CONFIRMATORY INDICATORS - Confirming Signals]")
        
        print("[5/11] Fear & Greed Index...")
        fg_value, fg_sentiment = self.get_fear_greed_index()
        fg_score = self._convert_to_score(fg_value, fg_sentiment, "fear_greed")
        print(f"      Fear & Greed: {fg_sentiment} -> Score: {fg_score:+d}")
        
        print("[6/11] Trend Strength...")
        trend = self.get_trend_strength()
        if trend['strength'] >= 8:
            trend_score = 2
        elif trend['strength'] >= 6:
            trend_score = 1
        elif trend['strength'] <= 2:
            trend_score = -2
        elif trend['strength'] <= 4:
            trend_score = -1
        else:
            trend_score = 0
        print(f"      Trend: {trend['direction']} ({trend['strength']}/10) -> Score: {trend_score:+d}")
        
        print("[7/11] Volume Confirmation...")
        volume = self.get_volume_confirmation()
        volume_score = volume['signal']
        print(f"      Volume: {volume['volume_trend']} -> Score: {volume_score:+d}")
        
        print("[8/11] Bollinger Bands...")
        bb_signal = self.get_bollinger_bands()
        bb_score = self._convert_to_score(0, bb_signal, "bollinger")
        print(f"      Bollinger: {bb_signal} -> Score: {bb_score:+d}")
        
        print("[9/12] Volume Profile...")
        vol_profile = self.get_volume_profile()
        vol_profile_score = vol_profile['signal']
        print(f"      Volume Profile: {vol_profile['volume_trend']} -> Score: {vol_profile_score:+d}")
        
        print("[10/12] Open Interest...")
        oi_signal = self.get_open_interest_trend()
        oi_score = self._convert_to_score(0, oi_signal, "oi")
        print(f"      Open Interest: {oi_signal} -> Score: {oi_score:+d}")
        
        print("[11/12] Funding Rate...")
        fr_signal = self.get_funding_rate()
        fr_score = self._convert_to_score(0, fr_signal, "funding")
        print(f"      Funding Rate: {fr_signal} -> Score: {fr_score:+d}")

        print("[12/12] Dollar Strength...")
        dollar = self.get_dollar_strength()
        dollar_score = dollar['score']
        print(f"      Dollar: {dollar['trend']} -> Score: {dollar_score:+d}")
        
        confirmatory_total = (fg_score + trend_score + volume_score + bb_score +
                            vol_profile_score + oi_score + fr_score + dollar_score)
        
        # TOTAL CALCULATION
        total_score = early_reversal_total + confirmatory_total
        max_score = 24  # 12 indicators × 2
        
        print(f"\n[CALCULATION]")
        print(f"Early Reversal Score: {early_reversal_total:+d} / 8")
        print(f"Confirmatory Score: {confirmatory_total:+d} / 16")
        print(f"Total Score: {total_score:+d} / {max_score}")
        
        # Determine sentiment
        if total_score >= 11:
            sentiment = "ULTRA BULLISH"
        elif total_score >= 6:
            sentiment = "BULLISH"
        elif total_score <= -11:
            sentiment = "ULTRA BEARISH"
        elif total_score <= -6:
            sentiment = "BEARISH"
        else:
            sentiment = "CONSOLIDATION"
        
        print(f"Sentiment: {sentiment}")
        
        # Store results
        self.previous_sentiment = self.current_sentiment
        self.current_sentiment = sentiment
        self.last_update = datetime.now()
        
        # Generate signal
        signal = self.signal_generator.generate_signal(
            total_score, sentiment, self.previous_sentiment
        )
        
        if signal:
            print(self.signal_generator.format_signal_alert(signal))
        
        self.indicator_scores = {
            'early_reversal': {
                'rsi_divergence': rsi_div_score,
                'macd_divergence': macd_div_score,
                'whale_activity': whale_score,
                'structure_break': structure_score,
                'total': early_reversal_total
            },
            'confirmatory': {
                'fear_greed': fg_score,
                'trend_strength': trend_score,
                'volume': volume_score,
                'bollinger_bands': bb_score,
                'volume_profile': vol_profile_score,
                'open_interest': oi_score,
                'funding_rate': fr_score,
                'dollar_strength': dollar_score,
                'total': confirmatory_total
            }
        }
        
        changed = self.previous_sentiment != self.current_sentiment and self.previous_sentiment is not None
        
        return {
            'sentiment': sentiment,
            'indicators': self.indicator_scores,
            'changed': changed,
            'previous_sentiment': self.previous_sentiment,
            'timestamp': self.last_update.isoformat(),
            'total_score': total_score,
            'max_score': max_score,
            'signal': signal
        }


# Test
if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    result = analyzer.analyze_sentiment()
    print(f"\nFinal Result: {result['sentiment']}")
    print(f"Total Score: {result['total_score']:+d} / {result['max_score']}")
    print(f"Changed: {result['changed']}")
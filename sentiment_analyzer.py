f"""
Enhanced Crypto Market Sentiment Analyzer - Phase 3
10 scored indicators plus non-scoring data-quality/context feeds
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
    """Sentiment analyzer with 10 scored indicators and signal generation."""
    
    def __init__(self):
        self.current_sentiment = None
        self.previous_sentiment = None
        self.last_update = None
        self.indicator_scores = {}
        self.early_reversal_scores = {}
        self.confirmatory_scores = {}
        self.data_quality = {}
        
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
        self.data_quality = {}

    @staticmethod
    def _fetch_klines(interval: str, limit: int, futures: bool = False) -> list:
        """Fetch validated Binance candles or raise a data-source error."""
        base = 'https://fapi.binance.com/fapi/v1/klines' if futures else 'https://data-api.binance.vision/api/v3/klines'
        response = requests.get(
            base,
            params={'symbol': 'BTCUSDT', 'interval': interval, 'limit': limit},
            headers={'User-Agent': 'BTC-Sentiment-Analyzer/1.0'},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or len(payload) < 2 or any(not isinstance(row, list) or len(row) < 8 for row in payload):
            raise ValueError(f'Binance returned an invalid {interval} kline payload')
        return payload
    
    # ==================== EARLY REVERSAL INDICATORS ====================
    # (Leading indicators - predict change)
    
    def get_rsi_divergence(self) -> Dict:
        """[EARLY] Detect confirmed daily RSI divergence using price pivots."""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': '1d',
                'limit': 120
            }
            
            klines = self._fetch_klines('1d', 120)
            closes = [float(k[4]) for k in klines]
            
            if len(closes) < 40:
                return {'type': 'None', 'signal': 0}

            deltas = np.diff(closes)
            gains = np.maximum(deltas, 0)
            losses = np.maximum(-deltas, 0)
            avg_gain = np.mean(gains[:14])
            avg_loss = np.mean(losses[:14])
            rsi_values = [50.0]
            for index in range(14, len(deltas) + 1):
                avg_gain = (avg_gain * 13 + gains[index - 1]) / 14
                avg_loss = (avg_loss * 13 + losses[index - 1]) / 14
                rs = avg_gain / avg_loss if avg_loss else 100
                rsi_values.append(100 - (100 / (1 + rs)))
            rsi_values = [rsi_values[0]] * (len(closes) - len(rsi_values)) + rsi_values

            # Compare the latest two confirmed pivot lows/highs in a short
            # recent window. The latest candle is not treated as a pivot.
            pivots_low = [i for i in range(2, len(closes) - 2)
                          if closes[i] < closes[i-1] and closes[i] <= closes[i+1]
                          and closes[i] < closes[i-2] and closes[i] <= closes[i+2]]
            pivots_high = [i for i in range(2, len(closes) - 2)
                           if closes[i] > closes[i-1] and closes[i] >= closes[i+1]
                           and closes[i] > closes[i-2] and closes[i] >= closes[i+2]]
            pivots_low = [i for i in pivots_low if i >= len(closes) - 45]
            pivots_high = [i for i in pivots_high if i >= len(closes) - 45]
            self.rsi_history = rsi_values
            if len(pivots_low) >= 2:
                first, second = pivots_low[-2:]
                if closes[second] < closes[first] and rsi_values[second] > rsi_values[first] + 3:
                    return {'type': 'Bullish Divergence', 'signal': 2}
            if len(pivots_high) >= 2:
                first, second = pivots_high[-2:]
                if closes[second] > closes[first] and rsi_values[second] < rsi_values[first] - 3:
                    return {'type': 'Bearish Divergence', 'signal': -2}
            
            return {'type': 'None', 'signal': 0}
        except Exception as e:
            print(f"Error in RSI Divergence: {e}")
            return {'type': 'None', 'signal': 0}
    
    def get_macd_divergence(self) -> Dict:
        """[EARLY] Daily MACD momentum and histogram direction."""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': '1d',
                'limit': 100
            }
            
            klines = self._fetch_klines('1d', 100)
            closes = [float(k[4]) for k in klines]
            
            if len(closes) < 35:
                return {'type': 'None', 'signal': 0}
            series = pd.Series(closes)
            ema12 = series.ewm(span=12, adjust=False).mean()
            ema26 = series.ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal
            macd_line = float(macd.iloc[-1])
            signal_line = float(signal.iloc[-1])
            hist_now = float(histogram.iloc[-1])
            hist_prior = float(histogram.iloc[-2])
            self.macd_history = histogram.tolist()[-20:]
            self.price_history = closes

            if macd_line > signal_line and hist_now > hist_prior:
                return {'type': 'Bullish Momentum', 'signal': 2 if hist_now > 0 else 1}
            if macd_line < signal_line and hist_now < hist_prior:
                return {'type': 'Bearish Momentum', 'signal': -2 if hist_now < 0 else -1}
            return {'type': 'Neutral Momentum', 'signal': 0}
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
        """[CONFIRM] Combine ATR-normalized momentum with directional ADX."""
        try:
            rows = self._fetch_klines('1d', 100)
            if len(rows) < 35:
                return {'strength': 5, 'direction': 'Neutral', 'description': 'Insufficient data', 'quality': {'status': 'degraded', 'reason': 'insufficient daily candles'}}
            highs = np.array([float(row[2]) for row in rows])
            lows = np.array([float(row[3]) for row in rows])
            closes = np.array([float(row[4]) for row in rows])
            previous_closes = np.roll(closes, 1)
            previous_closes[0] = closes[0]
            true_range = np.maximum(highs - lows, np.maximum(abs(highs - previous_closes), abs(lows - previous_closes)))
            atr = pd.Series(true_range).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
            up_move = np.diff(highs, prepend=highs[0])
            down_move = -np.diff(lows, prepend=lows[0])
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
            plus_di = 100 * pd.Series(plus_dm).ewm(alpha=1 / 14, adjust=False).mean().to_numpy() / np.maximum(atr, 1e-9)
            minus_di = 100 * pd.Series(minus_dm).ewm(alpha=1 / 14, adjust=False).mean().to_numpy() / np.maximum(atr, 1e-9)
            dx = 100 * abs(plus_di - minus_di) / np.maximum(plus_di + minus_di, 1e-9)
            adx = pd.Series(dx).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
            current_atr = float(atr[-1])
            momentum_5d_atr = ((closes[-1] - closes[-6]) / max(current_atr, 1e-9))
            adx_value = float(adx[-1])
            plus_value = float(plus_di[-1])
            minus_value = float(minus_di[-1])
            direction = 'Up' if plus_value > minus_value and momentum_5d_atr > 0 else 'Down' if minus_value > plus_value and momentum_5d_atr < 0 else 'Neutral'
            strength = 5
            if adx_value >= 25:
                strength += 2 if direction != 'Neutral' else 0
            elif adx_value >= 18 and direction != 'Neutral':
                strength += 1
            if abs(momentum_5d_atr) >= 2:
                strength += 2 if direction != 'Neutral' else 0
            elif abs(momentum_5d_atr) >= 1:
                strength += 1 if direction != 'Neutral' else 0
            if direction == 'Down':
                strength = 10 - strength
            strength = max(1, min(10, strength))
            return {
                'strength': strength,
                'direction': direction,
                'description': f'ADX {adx_value:.1f}; +DI {plus_value:.1f}; -DI {minus_value:.1f}; momentum {momentum_5d_atr:.2f} ATR',
                'adx': round(adx_value, 2),
                'plus_di': round(plus_value, 2),
                'minus_di': round(minus_value, 2),
                'atr': round(current_atr, 2),
                'momentum_5d_atr': round(float(momentum_5d_atr), 2),
                'quality': {'status': 'available', 'source': 'Binance BTCUSDT daily OHLCV', 'freshness': 'daily'}
            }
        except Exception as e:
            print(f"Error calculating ATR/ADX trend: {e}")
            return {'strength': 5, 'direction': 'Neutral', 'description': 'Trend data unavailable', 'quality': {'status': 'unavailable', 'reason': str(e)}}
    
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
            
            klines = self._fetch_klines('1d', 20)
            
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
    
    def get_open_interest_trend(self) -> Dict:
        """[CONFIRM] Score open interest only in combination with price direction."""
        try:
            url = "https://www.binance.com/fapi/v1/openInterest"
            params = {'symbol': 'BTCUSDT'}
            
            response = requests.get(url, params=params, headers={'User-Agent': 'BTC-Sentiment-Analyzer/1.0'}, timeout=10)
            response.raise_for_status()
            oi_payload = response.json()
            if not isinstance(oi_payload, dict) or 'openInterest' not in oi_payload:
                raise ValueError('Binance returned an invalid open-interest payload')
            current_oi = float(oi_payload['openInterest'])
            
            cache_file = "oi_cache.json"
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    previous_oi = cache.get('last_oi', current_oi)
            else:
                previous_oi = current_oi
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'last_oi': current_oi}, f)
            
            oi_change = (current_oi / previous_oi - 1) if previous_oi else 0
            price_rows = self._fetch_klines('4h', 2)
            price_change = float(price_rows[-1][4]) / float(price_rows[-2][4]) - 1 if len(price_rows) >= 2 else 0
            oi_direction = "Increasing" if oi_change >= 0.05 else "Decreasing" if oi_change <= -0.05 else "Stable"
            price_direction = "Up" if price_change > 0 else "Down" if price_change < 0 else "Flat"
            # Aligned price and OI changes are the only high-confidence cases;
            # conflicting changes are deliberately neutral rather than guessed.
            score = 2 if oi_direction == "Increasing" and price_direction == "Up" else -2 if oi_direction == "Increasing" and price_direction == "Down" else 0
            return {'trend': oi_direction, 'price_direction': price_direction, 'change_pct': round(oi_change * 100, 2), 'score': score}
        except Exception as e:
            print(f"Error fetching Open Interest: {e}")
            return {'trend': 'Unavailable', 'price_direction': 'Unknown', 'change_pct': None, 'score': 0}
    
    def get_funding_rate(self) -> Dict:
        """[CONFIRM] Fetch funding and score crowded positioning contrarianly."""
        try:
            url = "https://www.binance.com/fapi/v1/fundingRate"
            params = {'symbol': 'BTCUSDT', 'limit': 1}
            
            response = requests.get(url, params=params, headers={'User-Agent': 'BTC-Sentiment-Analyzer/1.0'}, timeout=10)
            response.raise_for_status()
            funding_payload = response.json()
            if not isinstance(funding_payload, list) or not funding_payload or 'fundingRate' not in funding_payload[0]:
                raise ValueError('Binance returned an invalid funding payload')
            rate = float(funding_payload[0]['fundingRate'])
            
            score = -2 if rate > 0.0005 else 2 if rate < -0.0005 else 0
            return {'state': 'Positive' if rate > 0.0005 else 'Negative' if rate < -0.0005 else 'Neutral', 'rate': rate, 'score': score}
        except Exception as e:
            print(f"Error fetching Funding Rate: {e}")
            return {'state': 'Unavailable', 'rate': None, 'score': 0}
    
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
        """Analyze reliable indicators split into early and confirmatory sections."""
        
        print("\n" + "="*70)
        print(f"ANALYZING SENTIMENT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # EARLY REVERSAL INDICATORS (Leading - predict change)
        print("\n[EARLY REVERSAL INDICATORS - Leading Signals]")
        
        print("[1/10] RSI Divergence...")
        rsi_div = self.get_rsi_divergence()
        rsi_div_score = rsi_div['signal']
        print(f"      RSI Divergence: {rsi_div['type']} -> Score: {rsi_div_score:+d}")
        
        print("[2/10] MACD Momentum...")
        macd_div = self.get_macd_divergence()
        macd_div_score = macd_div['signal']
        print(f"      MACD Divergence: {macd_div['type']} -> Score: {macd_div_score:+d}")
        
        print("[context] Whale Activity (data quality only)...")
        whale = self.get_whale_accumulation()
        whale_score = whale['signal']
        print(f"      Whales: {whale['activity']} -> Score: {whale_score:+d}")
        
        print("[3/10] Break of Structure...")
        structure = self.get_structure_break()
        structure_score = structure['signal']
        print(f"      Structure: {structure['structure']} -> Score: {structure_score:+d}")
        
        early_reversal_total = rsi_div_score + macd_div_score + whale_score + structure_score
        
        # CONFIRMATORY INDICATORS (Lagging - confirm change)
        print("\n[CONFIRMATORY INDICATORS - Confirming Signals]")
        
        print("[4/10] Fear & Greed Index...")
        fg_value, fg_sentiment = self.get_fear_greed_index()
        fg_score = self._convert_to_score(fg_value, fg_sentiment, "fear_greed")
        print(f"      Fear & Greed: {fg_sentiment} -> Score: {fg_score:+d}")
        
        print("[5/10] Trend Strength...")
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
        
        print("[context] Volume Confirmation (context only)...")
        volume = self.get_volume_confirmation()
        volume_score = 0
        print(f"      Volume: {volume['volume_trend']} -> Score: excluded (profile is the scored participation feed)")
        
        print("[6/10] Bollinger Bands...")
        bb_signal = self.get_bollinger_bands()
        bb_score = self._convert_to_score(0, bb_signal, "bollinger")
        print(f"      Bollinger: {bb_signal} -> Score: {bb_score:+d}")
        
        print("[7/10] Volume Profile...")
        vol_profile = self.get_volume_profile()
        vol_profile_score = vol_profile['signal']
        print(f"      Volume Profile: {vol_profile['volume_trend']} -> Score: {vol_profile_score:+d}")
        
        print("[8/10] Open Interest...")
        oi_signal = self.get_open_interest_trend()
        oi_score = oi_signal['score']
        print(f"      Open Interest: {oi_signal['trend']} + price {oi_signal['price_direction']} -> Score: {oi_score:+d}")
        
        print("[9/10] Funding Rate...")
        fr_signal = self.get_funding_rate()
        fr_score = fr_signal['score']
        print(f"      Funding Rate: {fr_signal['state']} (contrarian) -> Score: {fr_score:+d}")

        print("[10/10] Dollar Strength...")
        dollar = self.get_dollar_strength()
        dollar_score = dollar['score']
        print(f"      Dollar: {dollar['trend']} -> Score: {dollar_score:+d}")

        self.data_quality = {
            'rsi_divergence': {'status': 'available' if len(self.rsi_history) >= 40 else 'unavailable', 'source': 'Binance BTCUSDT daily OHLCV'},
            'macd_momentum': {'status': 'available' if len(self.macd_history) >= 2 else 'unavailable', 'source': 'Binance BTCUSDT daily OHLCV'},
            'whale_activity': {'status': 'unavailable' if 'unavailable' in str(whale.get('description', '')).lower() else 'available', 'source': 'No configured on-chain provider'},
            'structure_break': {'status': 'available' if structure.get('structure') not in ('Error', 'Insufficient Data') else 'unavailable', 'source': 'Binance BTCUSDT 4H OHLCV'},
            'fear_greed': {'status': 'available', 'source': 'Alternative.me'},
            'trend_strength': trend.get('quality', {'status': 'available', 'source': 'Binance BTCUSDT daily OHLCV'}),
            'volume_confirmation': {'status': 'available' if volume.get('current_volume', 0) else 'unavailable', 'role': 'context_only'},
            'bollinger_bands': {'status': 'available', 'source': 'Binance BTCUSDT daily OHLCV'},
            'volume_profile': {'status': 'available' if vol_profile.get('current_volume', 0) else 'unavailable', 'source': 'Binance BTCUSDT daily OHLCV'},
            'open_interest': {'status': 'available' if oi_signal.get('trend') != 'Unavailable' else 'unavailable', 'source': 'Binance Futures + 4H price context'},
            'funding_rate': {'status': 'available' if fr_signal.get('state') != 'Unavailable' else 'unavailable', 'source': 'Binance Futures'},
            'dollar_strength': {'status': 'available' if dollar.get('available') else 'unavailable', 'source': dollar.get('source', 'FRED')},
        }
        
        confirmatory_total = (fg_score + trend_score + volume_score + bb_score +
                            vol_profile_score + oi_score + fr_score + dollar_score)
        
        # TOTAL CALCULATION
        total_score = early_reversal_total + confirmatory_total
        max_score = 20  # 10 directional feeds × 2; unavailable/context feeds score zero
        
        print(f"\n[CALCULATION]")
        print(f"Early Reversal Score: {early_reversal_total:+d} / 6")
        print(f"Confirmatory Score: {confirmatory_total:+d} / 14")
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
            'metrics': {
                'volume': {
                    'confirmation': volume,
                    'profile': vol_profile,
                },
                'trend': trend,
                'open_interest': oi_signal,
                'funding': fr_signal,
            },
            'data_quality': self.data_quality,
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

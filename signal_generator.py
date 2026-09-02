"""
Signal Generator - Phase 3
Generates Scout/Core/Max buy/sell signals based on sentiment analysis
"""

from datetime import datetime
from typing import Dict, Optional, List
import json
import os

class SignalGenerator:
    """Generate trading signals based on sentiment scores."""
    
    def __init__(self, signal_history_file: str = "signal_history.json"):
        self.signal_history_file = signal_history_file
        self.signal_history = self._load_signal_history()
        self.last_signal = None
        self.current_position = None  # For tracking
    
    def _load_signal_history(self) -> List[Dict]:
        """Load signal history from file."""
        if os.path.exists(self.signal_history_file):
            try:
                with open(self.signal_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_signal_history(self):
        """Save signal history to file."""
        with open(self.signal_history_file, 'w', encoding='utf-8') as f:
            json.dump(self.signal_history, f, indent=2, ensure_ascii=False)
    
    def generate_signal(self, total_score: int, sentiment: str, 
                       previous_sentiment: Optional[str] = None) -> Optional[Dict]:
        """
        Generate buy/sell signal based on sentiment score.
        
        Returns:
            Signal dict with type, direction, size recommendation, or None if no signal
        """
        
        # Determine signal type based on score
        signal_type = None
        direction = None
        size_recommendation = None
        
        # ENTRY SIGNALS (Bullish)
        if sentiment in ["BULLISH", "ULTRA BULLISH"]:
            if total_score >= 13:
                signal_type = "Max Entry"
                direction = "BUY"
                size_recommendation = "50%+"
            elif total_score >= 9:
                signal_type = "Core Entry"
                direction = "BUY"
                size_recommendation = "30-40%"
            elif total_score >= 5:
                signal_type = "Scout Entry"
                direction = "BUY"
                size_recommendation = "5-10%"
        
        # EXIT SIGNALS (Bearish)
        elif sentiment in ["BEARISH", "ULTRA BEARISH"]:
            if total_score <= -13:
                signal_type = "Max Exit"
                direction = "SELL"
                size_recommendation = "50%+"
            elif total_score <= -9:
                signal_type = "Core Exit"
                direction = "SELL"
                size_recommendation = "30-40%"
            elif total_score <= -5:
                signal_type = "Scout Exit"
                direction = "SELL"
                size_recommendation = "5-10%"
        
        # No signal for consolidation
        else:
            return None
        
        # Only generate signal if there's a valid signal type
        if signal_type is None:
            return None
        
        # Check if this is a NEW signal (avoid duplicate alerts)
        if self.last_signal and self.last_signal['type'] == signal_type:
            return None  # Same signal type, don't repeat
        
        signal = {
            'timestamp': datetime.now().isoformat(),
            'type': signal_type,
            'direction': direction,
            'sentiment': sentiment,
            'score': total_score,
            'size': size_recommendation,
            'previous_sentiment': previous_sentiment
        }
        
        # Save to history
        self.signal_history.append(signal)
        self._save_signal_history()
        
        # Update last signal
        self.last_signal = signal
        
        return signal
    
    def get_signal_emoji(self, signal_type: str) -> str:
        """Get emoji for signal type."""
        emojis = {
            "Scout Entry": "🟢",
            "Core Entry": "🟢🟢",
            "Max Entry": "🟢🟢🟢",
            "Scout Exit": "🔴",
            "Core Exit": "🔴🔴",
            "Max Exit": "🔴🔴🔴"
        }
        return emojis.get(signal_type, "")
    
    def format_signal_alert(self, signal: Dict) -> str:
        """Format signal for display/alert."""
        emoji = self.get_signal_emoji(signal['type'])
        
        alert = f"""
╔════════════════════════════════════════╗
║          🚨 TRADING SIGNAL 🚨          ║
╠════════════════════════════════════════╣
║ {emoji} {signal['type']:<35} {emoji} ║
║ Direction: {signal['direction']:<28} ║
║ Sentiment: {signal['sentiment']:<28} ║
║ Score: {signal['score']:+d}/24  ║
║ Position Size: {signal['size']:<22} ║
║ Time: {signal['timestamp']:<32} ║
╚════════════════════════════════════════╝
"""
        return alert
    
    def get_recent_signals(self, limit: int = 10) -> List[Dict]:
        """Get recent signals."""
        return self.signal_history[-limit:]
    
    def print_signal_history(self, limit: int = 10):
        """Print recent signal history."""
        recent = self.get_recent_signals(limit)
        
        print("\n" + "="*60)
        print(f"RECENT SIGNALS (Last {len(recent)})")
        print("="*60)
        
        if not recent:
            print("No signals yet.")
            return
        
        for signal in recent:
            emoji = self.get_signal_emoji(signal['type'])
            print(f"\n{emoji} {signal['type']} - {signal['sentiment']}")
            print(f"   Score: {signal['score']:+d} | Size: {signal['size']}")
            print(f"   Time: {signal['timestamp']}")
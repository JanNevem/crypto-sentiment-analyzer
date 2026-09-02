"""
Enhanced Alert System - Phase 3 Complete
Sends alerts with Phase 3 indicator structure to Telegram and console
"""

import os
import sys
from datetime import datetime
from typing import Optional
import json
import requests

class AlertSystem:
    """Enhanced alert system with Phase 3 indicators."""
    
    def __init__(self, log_file: str = "sentiment_history.json", 
                 telegram_token: Optional[str] = None,
                 telegram_chat_id: Optional[str] = None):
        self.log_file = log_file
        self.alert_history = self._load_history()
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
    
    def _load_history(self) -> list:
        """Load alert history from file."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_history(self):
        """Save alert history to file."""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.alert_history, f, indent=2, ensure_ascii=False)
    
    def send_alert(self, 
                   sentiment: str, 
                   previous_sentiment: Optional[str],
                   confidence: float = 0.0,
                   indicators: Optional[dict] = None):
        """Send alert for sentiment change with all indicators."""
        
        timestamp = datetime.now()
        indicators = indicators or {}
        
        # Only alert if sentiment changed
        if previous_sentiment is None or sentiment == previous_sentiment:
            return
        
        alert_message = self._format_alert(
            sentiment, 
            previous_sentiment, 
            confidence, 
            indicators,
            timestamp
        )
        
        # Print to console with colors
        self._print_alert(alert_message, sentiment)
        
        # Log to file
        self._log_alert(alert_message, sentiment, timestamp)
        
        # Try to send system notification
        self._send_system_notification(sentiment, previous_sentiment, confidence)
        
        # Send Telegram alert
        self._send_telegram_alert(sentiment, previous_sentiment, confidence, indicators, timestamp)
    
    def _format_alert(self, 
                      sentiment: str, 
                      previous_sentiment: str,
                      confidence: float,
                      indicators: dict,
                      timestamp: datetime) -> str:
        """Format alert message with Phase 3 indicators."""
        
        # Get indicator sections
        early = indicators.get('early_reversal', {})
        confirm = indicators.get('confirmatory', {})
        
        # Build Early Reversal section
        early_section = f"""
📊 Early Reversal Indicators (Leading Signals):
   • RSI Divergence: {early.get('rsi_divergence', 0):+d} (Score: {early.get('rsi_divergence', 0):+d})
   • MACD Divergence: {early.get('macd_divergence', 0):+d} (Score: {early.get('macd_divergence', 0):+d})
   • Whale Activity: {early.get('whale_activity', 0):+d} (Score: {early.get('whale_activity', 0):+d})
   • Structure Break: {early.get('structure_break', 0):+d} (Score: {early.get('structure_break', 0):+d})
   └─ Early Reversal Total: {early.get('total', 0):+d}/8"""
        
        # Build Confirmatory section
        confirm_section = f"""
📊 Confirmatory Indicators (Confirming Signals):
   • Fear & Greed: {confirm.get('fear_greed', 0):+d}
   • Trend Strength: {confirm.get('trend_strength', 0):+d}
   • Volume: {confirm.get('volume', 0):+d}
   • Bollinger Bands: {confirm.get('bollinger_bands', 0):+d}
   • Volume Profile: {confirm.get('volume_profile', 0):+d}
   • Open Interest: {confirm.get('open_interest', 0):+d}
   • Funding Rate: {confirm.get('funding_rate', 0):+d}
   • Dollar Strength: {confirm.get('dollar_strength', 0):+d}
   └─ Confirmatory Total: {confirm.get('total', 0):+d}/16"""
        
        message = f"""
╔════════════════════════════════════════════════════════════╗
║                    🚨 SENTIMENT ALERT 🚨                   ║
╚════════════════════════════════════════════════════════════╝

⏰ Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

📊 Sentiment Change:
   {previous_sentiment} → {sentiment}
   
📈 Confidence: {confidence:.1f}%

{early_section}

{confirm_section}

═══════════════════════════════════════════════════════════════
"""
        return message
    
    def _print_alert(self, alert_message: str, sentiment: str):
        """Print alert to console with formatting."""
        print(alert_message)
    
    def _log_alert(self, alert_message: str, sentiment: str, timestamp: datetime):
        """Log alert to history file."""
        
        alert_entry = {
            'timestamp': timestamp.isoformat(),
            'sentiment': sentiment,
            'message': alert_message
        }
        
        self.alert_history.append(alert_entry)
        self._save_history()
        
        # Also log to file
        try:
            with open('sentiment_alerts.log', 'a', encoding='utf-8') as f:
                f.write(f"\n{alert_message}\n")
        except Exception as e:
            print(f"Error logging to file: {e}")
    
    def _send_system_notification(self, sentiment: str, previous_sentiment: str, confidence: float):
        """Send system notification (Windows/Mac/Linux)."""
        try:
            if sys.platform == 'win32':
                # Windows notification
                import subprocess
                title = f"Sentiment Change: {previous_sentiment} → {sentiment}"
                message = f"Confidence: {confidence:.1f}%"
                subprocess.run([
                    'powershell', '-Command',
                    f'[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; '
                    f'$APP_ID = "CryptoAnalyzer"; '
                    f'[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($APP_ID).Show([Windows.UI.Notifications.ToastNotification]::new([xml]'
                    f'"<toast><visual><binding template=\"ToastText02\"><text id=\"1\">{title}</text><text id=\"2\">{message}</text></binding></visual></toast>"));'
                ], check=False)
        except Exception as e:
            pass  # Silently fail if notification not available
    
    def _send_telegram_alert(self, sentiment: str, previous_sentiment: str, confidence: float, indicators: dict, timestamp: datetime):
        """Send alert to Telegram."""
        
        if not self.telegram_token or not self.telegram_chat_id:
            return
        
        try:
            early = indicators.get('early_reversal', {})
            confirm = indicators.get('confirmatory', {})
            
            message = f"""
🚨 *SENTIMENT ALERT*

*Sentiment Change:*
{previous_sentiment} → {sentiment}

*Confidence:* {confidence:.1f}%

*Early Reversal:* {early.get('total', 0):+d}/8
        *Dollar Strength:* {confirm.get('dollar_strength', 0):+d}
*Confirmatory:* {confirm.get('total', 0):+d}/16

*Time:* {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, data=data, timeout=5)
            
            if response.status_code == 200:
                print(f"✅ Telegram alert sent successfully!")
            else:
                print(f"⚠️ Failed to send Telegram alert: {response.text}")
        
        except Exception as e:
            print(f"⚠️ Error sending Telegram alert: {e}")
    
    def get_history(self, limit: int = 10) -> list:
        """Get recent alerts."""
        return self.alert_history[-limit:]
    
    def print_history(self, limit: int = 10):
        """Print recent alert history."""
        recent = self.get_history(limit)
        
        print("\n" + "="*70)
        print(f"RECENT ALERTS (Last {len(recent)})")
        print("="*70)
        
        if not recent:
            print("No alerts yet.")
            return
        
        for alert in recent:
            print(f"\n{alert['timestamp']} - {alert['sentiment']}")
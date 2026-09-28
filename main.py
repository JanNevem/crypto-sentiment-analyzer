"""
Main entry point for Crypto Sentiment Analyzer - Phase 3
Runs continuous analysis with signal generation
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from sentiment_analyzer import SentimentAnalyzer
from alert_system import AlertSystem
from visual_state import update_visual_state

# Telegram credentials must be provided through environment variables.
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
STATE_FILE = os.getenv("SENTIMENT_STATE_FILE", "sentiment_state.json")


def print_sentiment_display(result):
    """Display sentiment analysis results in a formatted way."""
    
    sentiment = result['sentiment']
    total_score = result['total_score']
    max_score = result['max_score']
    changed = result['changed']
    indicators = result['indicators']
    
    # Sentiment emoji
    sentiment_emoji = {
        'ULTRA BULLISH': '🟢🟢🟢',
        'BULLISH': '🟢🟢',
        'CONSOLIDATION': '🟡',
        'BEARISH': '🔴🔴',
        'ULTRA BEARISH': '🔴🔴🔴'
    }
    
    emoji = sentiment_emoji.get(sentiment, '⚪')
    
    print("\n" + "="*70)
    print(f"{emoji} SENTIMENT: {sentiment} {emoji}")
    print(f"Score: {total_score:+d}/{max_score} | Changed: {changed}")
    visual = result.get('visual_state')
    if visual:
        print(f"Visual: {visual['regime'].upper()} | 4-hour slot: {visual['slot_utc']} | Updated: {visual['updated_now']}")
    print("="*70)
    
    # EARLY REVERSAL INDICATORS
    print("\n📊 EARLY REVERSAL INDICATORS (Leading Signals):")
    early = indicators['early_reversal']
    print(f"  RSI Divergence: {early['rsi_divergence']:+d}")
    print(f"  MACD Divergence: {early['macd_divergence']:+d}")
    print(f"  Whale Activity: {early['whale_activity']:+d}")
    print(f"  Structure Break: {early['structure_break']:+d}")
    print(f"  └─ Early Reversal Total: {early['total']:+d}/8")
    
    # CONFIRMATORY INDICATORS
    print("\n📊 CONFIRMATORY INDICATORS (Confirming Signals):")
    confirm = indicators['confirmatory']
    print(f"  Fear & Greed: {confirm['fear_greed']:+d}")
    print(f"  Trend Strength: {confirm['trend_strength']:+d}")
    print(f"  Volume: {confirm['volume']:+d}")
    print(f"  Bollinger Bands: {confirm['bollinger_bands']:+d}")
    print(f"  Volume Profile: {confirm['volume_profile']:+d}")
    print(f"  Open Interest: {confirm['open_interest']:+d}")
    print(f"  Funding Rate: {confirm['funding_rate']:+d}")
    print(f"  Dollar Strength: {confirm['dollar_strength']:+d}")
    print(f"  └─ Confirmatory Total: {confirm['total']:+d}/16")
    
    # Signal if generated
    if result.get('signal'):
        signal = result['signal']
        print(f"\n🚨 SIGNAL GENERATED: {signal['type']}")
        print(f"   Direction: {signal['direction']}")
        print(f"   Position Size: {signal['size']}")


def _load_previous_sentiment():
    """Load the previous sentiment so scheduled runs can detect changes."""
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as handle:
            return json.load(handle).get('sentiment')
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _save_sentiment(result):
    """Persist only the small amount of state required by the next run."""
    with open(STATE_FILE, 'w', encoding='utf-8') as handle:
        json.dump({'sentiment': result['sentiment'], 'timestamp': result['timestamp']}, handle)


def run_once(analyzer, alert_system):
    """Run one analysis cycle and exit, suitable for an external scheduler."""
    analyzer.current_sentiment = _load_previous_sentiment()
    result = analyzer.analyze_sentiment()
    result['visual_state'] = update_visual_state(result)
    print_sentiment_display(result)

    if result.get('signal') and result.get('changed'):
        alert_system.send_alert(
            sentiment=result['sentiment'],
            previous_sentiment=result['previous_sentiment'],
            indicators=result['indicators']
        )

    _save_sentiment(result)
    return result


def run_watch(analyzer, alert_system, interval):
    """Run continuous sentiment analysis."""
    
    print(f"\n{'='*70}")
    print(f"STARTING CONTINUOUS ANALYSIS - Interval: {interval}s")
    print(f"{'='*70}")
    
    cycle = 0
    
    try:
        while True:
            cycle += 1
            print(f"\n[CYCLE {cycle}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Analyze sentiment
            result = analyzer.analyze_sentiment()
            
            # Display results
            print_sentiment_display(result)
            
            # Send alert if signal generated
            if result.get('signal'):
                alert_system.send_alert(
                    sentiment=result['sentiment'],
                    previous_sentiment=result['previous_sentiment'],
                    indicators=result['indicators']
                )
            
            # Wait for next interval
            print(f"\n⏳ Next update in {interval} seconds...")
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n\n✋ Analysis stopped by user")
    except Exception as e:
        print(f"\n❌ Error in analysis loop: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    
    parser = argparse.ArgumentParser(description='Crypto Sentiment Analyzer')
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Analysis interval in seconds (default: 300)'
    )
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Compatibility flag; continuous analysis is the default'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run one analysis cycle and exit'
    )
    
    args = parser.parse_args()
    
    # Initialize systems
    analyzer = SentimentAnalyzer()
    alert_system = AlertSystem(
        telegram_token=TELEGRAM_TOKEN,
        telegram_chat_id=TELEGRAM_CHAT_ID
    )
    
    if args.once:
        run_once(analyzer, alert_system)
    else:
        # --watch is retained for older launchers.
        run_watch(analyzer, alert_system, args.interval)


if __name__ == "__main__":
    main()

# Bitcoin Sentiment Analyzer — Indicator Audit

## Scope

This audit reviews the existing scoring pipeline in `sentiment_analyzer.py` and its supporting modules. The existing architecture, Telegram alerts, 4-hour analyzer cadence, and -2 to +2 score convention are preserved.

The code now has **10 scored feeds** plus non-scoring context/data-quality feeds. The scored feeds are split between early/reversal and confirmatory sections.

## Executive findings

1. **Whale Activity was not real market data.** The old fallback returned hard-coded inflow/outflow values and repeatedly produced a directional signal. It is now neutral when no real provider is configured.
2. **Trend Strength had a direction bug.** It used absolute price movement, so downward movement could not receive the intended negative adjustment. It now uses multi-day signed momentum and a normalized MACD tie-breaker, then the main analyzer adds ATR-normalized momentum and directional ADX.
3. **Break of Structure could not trigger correctly.** The old reference window included the current candle. It now compares against prior candles only.
4. **RSI Divergence was not divergence.** It now calculates RSI over daily candles and compares confirmed price pivot lows/highs with RSI pivots.
5. **MACD Divergence was not divergence.** It now calculates daily MACD, signal, and histogram direction and is labelled MACD momentum.
6. **Volume was double-counted.** Volume Confirmation and Volume Profile both reacted to recent volume/price. Volume Confirmation is now context-only; Volume Profile is the single scored participation feed.
7. **Open Interest and Funding were oversimplified.** Open Interest now requires price/OI context. Funding is scored contrarianly as crowding risk.
8. **The analyzer now persists explicit data quality.** Each feed records availability/source or a degraded/unavailable status, and unavailable feeds contribute zero rather than fabricated direction.

## Indicator-by-indicator assessment

| Feed | Status | Current treatment |
|---|---|---|
| RSI Divergence | Corrected | Daily Wilder-style RSI with confirmed pivot divergence; ±2 only for meaningful divergence |
| MACD Momentum | Corrected | Daily EMA12/26, signal 9, histogram direction; normalized trend context |
| Whale Activity | Removed from directional scoring | No configured reliable on-chain provider; unavailable data stays neutral |
| Break of Structure | Corrected | Prior-candle reference swing; current candle can now confirm a break |
| Fear & Greed | Kept | Slow crowd context; retains documented score mapping |
| Trend Strength | Recalibrated | ATR-normalized 5-day momentum plus ADX and +DI/-DI direction |
| Volume Confirmation | Context only | Not separately scored, preventing duplicate volume votes |
| Bollinger Bands | Kept | Existing breakout context remains for now; later calibration should distinguish continuation from exhaustion |
| Volume Profile | Kept as the one scored volume feed | OBV initialization and decreasing-OBV handling corrected |
| Open Interest | Rewritten | Requires OI change and 4H price direction; conflicting/ambiguous cases score zero |
| Funding Rate | Rewritten | Positive extreme funding is bearish crowding risk; negative extreme funding is bullish squeeze risk |
| Dollar Strength | Kept, low-frequency | Business-day macro context from FRED; unavailable data scores zero |

## Recommended architecture

### Directional trend block

Use EMA relationship/slope, ATR-normalized momentum, directional ADX, and market structure as related evidence. They should not become independent unlimited votes because they react to the same price move. The current implementation keeps ATR momentum and ADX inside the existing Trend Strength feed rather than increasing the indicator count.

### Participation and positioning block

Use one scored volume feed, plus price/OI context and funding crowding. Volume confirmation remains visible as context but does not vote separately.

### Risk, sentiment, and reversal block

Use Fear & Greed, Bollinger context, real RSI divergence, and slow dollar strength. Missing external data contributes zero with an explicit unavailable status.

## Stage status

**Stage 1 — Correctness fixes is complete.** False whale data was removed, signed momentum was fixed, structure break references were corrected, and OBV initialization/decreasing handling were fixed.

**Stage 2 — Redundancy and data quality is complete.** Duplicate volume voting was removed. Analyzer results now persist a `data_quality` object for every scored/context feed. Unavailable feeds contribute zero.

**Stage 3 — Calibrated signals is complete.** ATR-normalized 5-day momentum and directional ADX (+DI/-DI) are integrated into Trend Strength without adding separate full-strength votes.

**Stage 4 — Stability and alerts is complete.** Sentiment transitions and Telegram alerts require two consecutive matching analyzer cycles. A first-cycle candidate is retained as pending state rather than immediately changing the displayed regime.

## Next calibration work

The next work should use fresh persisted analyzer cycles to calibrate thresholds, not add more indicators immediately. We should inspect the distribution of ATR momentum, ADX, RSI/MACD signals, OI/funding states, unavailable feeds, and sentiment transitions over several days before changing weights or thresholds.

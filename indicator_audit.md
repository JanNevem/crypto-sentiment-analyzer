# Bitcoin Sentiment Analyzer — Indicator Audit

## Scope

This audit reviews the existing scoring pipeline in `sentiment_analyzer.py` and its supporting modules. It does **not** change production scoring. The existing architecture, Telegram alerts, 4-hour analyzer cadence, and -2 to +2 score convention are preserved.

The code currently scores **12 feeds** (despite older comments saying 13): four early/reversal feeds and eight confirmatory feeds.

## Executive findings

1. **Whale Activity is not real market data.** The fallback returns a hard-coded `inflow=50`, `outflow=75`, so the analyzer repeatedly produces an accumulation/bullish contribution even when no on-chain data was retrieved.
2. **Trend Strength has a direction bug.** It uses `abs(price_change)` and then checks whether that value is negative. Downward price movement therefore never receives the intended negative momentum adjustment.
3. **Break of Structure cannot trigger as written.** It compares the current close with a recent high/low window that includes the current candle's high/low. A close cannot be above its own candle high or below its own candle low.
4. **RSI Divergence is not divergence.** It calculates one RSI value from the full close series, then compares the latest price direction with RSI above/below 50. It does not compare price pivots against RSI pivots.
5. **MACD Divergence is not divergence.** It returns bullish/bearish from the sign of MACD, not from divergence. The MACD history stores MACD line values, but the reversal detector expects histogram history and is not used by the main analyzer.
6. **Volume is double-counted.** `Volume Confirmation` and `Volume Profile` both use recent volume and price direction, so one event can affect the score twice.
7. **The confirmatory trend feed is underpowered and partly disconnected.** It receives `rsi=50` and `signal_line=0` from the main analyzer, so its RSI component is permanently neutral and its MACD histogram is not a true MACD histogram.
8. **Open Interest and Funding are oversimplified.** Open-interest direction alone is not bullish/bearish; it must be combined with price direction. Positive funding is often a crowded-long risk signal, not automatically bullish.
9. **Bollinger scoring is too sparse.** Only a rare outside-band event scores ±2; normal trend continuation and mean-reversion context score zero.
10. **The 12-indicator total is not equally independent.** Price momentum, trend strength, structure, MACD, Bollinger, volume confirmation, volume profile, and open interest can all react to the same move.

## Indicator-by-indicator assessment

| Feed | Current status | Main issue | Recommendation |
|---|---|---|---|
| RSI Divergence | **Replace implementation** | Not true divergence; weekly data with only 14 candles is insufficient for robust pivots | Implement real pivot divergence on daily/4H data, or temporarily relabel it as RSI regime until then |
| MACD Divergence | **Replace implementation** | MACD sign is being called divergence; only 26 daily candles gives weak warm-up | Use normalized MACD histogram slope/cross on daily data; reserve divergence for a separate pivot detector |
| Whale Activity | **Remove until real source** | Hard-coded estimate creates a persistent artificial -1 | Return unavailable/neutral with explicit data quality; add a real provider later behind an optional connector |
| Break of Structure | **Fix** | Current candle included in breakout reference, making BoS impossible | Compare the completed candle close against prior swing high/low only; require retest/close confirmation |
| Fear & Greed | **Keep, reclassify** | Useful context but slow and sentiment-based; current scoring follows greed instead of using a documented policy | Keep as a low-weight crowd-positioning/context feed; use as contrarian risk at extremes or momentum-following consistently, not both |
| Trend Strength | **Rewrite** | Down-momentum sign bug; RSI always 50; absolute MACD threshold is not scale-normalized | Use normalized returns/ATR, EMA slope, and ADX; return direction and confidence separately |
| Volume Confirmation | **Keep, simplify** | Uses the latest potentially incomplete 1H candle and only says volume rising/falling, not whether price move is accepted | Use completed candles, relative volume, and price direction; make it a confirmation modifier, not a standalone directional score |
| Bollinger Bands | **Keep, recalibrate** | Outside-band breakout is rare and can flag exhaustion as continuation | Score bandwidth/regime and close location; treat band breaks as context until trend/volume confirms |
| Volume Profile | **Merge with volume** | Duplicates Volume Confirmation; OBV initialization has a self-comparison bug and decreasing OBV is neutral | Merge into one participation indicator using relative volume + OBV slope; one vote only |
| Open Interest | **Keep, rewrite** | Change from one 15-minute sample is noisy; rising OI alone has ambiguous meaning | Use multi-hour/daily change and combine with price: price up + OI up = trend participation; price down + OI up = leverage/liquidation risk |
| Funding Rate | **Keep, make contrarian** | Positive funding is not simply bullish; can indicate crowded longs | Use magnitude and persistence; positive extreme = bearish risk, negative extreme = bullish squeeze risk |
| Dollar Strength | **Keep, low weight** | Slow business-day macro data is valid but stale relative to 15-minute cycles | Keep as a macro regime modifier, not a full-frequency vote; document stale-data behavior |

## Recommended indicator architecture

### A. Directional trend (one vote per concept)

- Daily EMA20/EMA50 relationship and slope
- ADX or an equivalent trend-strength measure
- Market structure (higher highs/lows, confirmed break)
- Momentum normalized by ATR or percentage return

These should not all receive independent full-strength votes. A simple approach is to calculate a **trend block** with a capped contribution, for example -4 to +4.

### B. Participation and positioning (one combined block)

- Relative volume versus completed 20-day average
- OBV or volume delta slope
- Open-interest change paired with price direction
- Funding-rate crowding/contrarian risk

Cap this block separately so volume, OI, and funding cannot overwhelm price structure.

### C. Risk, sentiment, and reversal (context block)

- Fear & Greed as a slow crowd-risk input
- Real RSI divergence only when confirmed by pivots
- Bollinger bandwidth/close location for compression or exhaustion
- Dollar strength as a slow macro modifier

A missing external feed must contribute **0 with an unavailable status**, never a fabricated directional score.

## Candidates to add

### High value, low complexity

1. **ATR-normalized momentum** — distinguishes a meaningful move from ordinary BTC noise.
2. **ADX with DI direction** — ADX alone measures strength but not direction; +DI/-DI supplies that direction.
3. **EMA slope / distance from EMA50** — more stable than a single-candle price change.
4. **Realized volatility regime** — identifies whether signals are occurring in expansion or compression.
5. **Liquidation/derivatives stress**, only if a reliable data source is available; do not simulate it.

### Do not add yet

- More oscillators that duplicate RSI/MACD/Bollinger.
- More whale/on-chain feeds without a real authenticated data source.
- Social sentiment without a stable historical source and rate-limit handling.

## Suggested staged implementation

### Stage 1 — Correctness fixes

- Remove the hard-coded whale estimate from scoring; mark the feed unavailable.
- Fix structure break reference windows.
- Fix signed momentum in `TrendAnalyzer`.
- Fix OBV initialization and decreasing-OBV handling.
- Replace misleading “divergence” labels with correct calculations or neutral placeholders.
- Ensure only completed candles are used.

### Stage 2 — Reduce redundancy

- Merge Volume Confirmation and Volume Profile into one participation feed.
- Keep the public -2 to +2 convention, but cap related blocks so correlated feeds do not dominate.
- Preserve the existing dashboard schema by exposing detailed sub-metrics under `metrics` while keeping one score per concept.

### Stage 3 — Add calibrated signals

- Add ATR-normalized momentum.
- Add ADX/+DI/-DI as a properly computed trend-strength feed.
- Add volatility regime.
- Backtest thresholds against persisted price history before enabling alerts.

### Stage 4 — Stability and alerts

- Require two consecutive analyzer cycles for a sentiment transition.
- Require stronger evidence for Telegram alerts than for dashboard display.
- Log each feed's value, score, freshness, and unavailable reason so later calibration is evidence-based.

## Immediate recommendation

Do **not** add more indicators yet. First fix the false data and broken calculations, merge duplicate volume signals, and add an explicit data-quality field. Then add ATR-normalized momentum and directional ADX. This will improve reliability more than increasing the indicator count.

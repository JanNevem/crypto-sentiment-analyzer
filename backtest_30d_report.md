# BTC Corrected Indicator Backtest — 30 Days

## Method

This is a non-lookahead daily backtest on real BTCUSDT candles from Binance public market data. Each signal uses only data through the signal day close; the position is applied to the following day’s open-to-close return. Long exposure is used for composite score >= +3, short exposure for <= -3, and flat otherwise. A 0.10% transaction cost is charged on position changes.

The tested available historical feeds are RSI divergence, MACD momentum, the corrected 4-hour market-structure signal, ATR/ADX trend strength, volume profile, and Bollinger Bands. Whale activity, Fear & Greed, open interest, funding, and dollar strength are excluded because reliable historical values are not persisted by the current analyzer; they are not fabricated.

## Results

| Metric | Result |
|---|---:|
| Signal/trading days | 30 |
| Active long/short days | 9 |
| Strategy return after costs | -1.73% |
| Buy-and-hold open-to-close benchmark | 4.20% |
| Max drawdown | 4.86% |
| Annualized daily Sharpe (descriptive only) | -0.62 |
| Directional accuracy on active days | 22.2% |
| Active-day win rate | 22.2% |
| Long / short / flat days | 9 / 0 / 21 |

## Latest backtest observation

The final signal date was **2026-10-07** with composite score **-1** and position **0** for the following session. Its trend metrics were ADX **41.15**, +DI **29.97**, −DI **17.38**, and ATR-normalized 5-day momentum **-0.55**.

## Interpretation

This is a diagnostic sample, not evidence of a deployable trading edge. Thirty days is too short for robust validation, and the strategy intentionally omits several live feeds because their historical series are unavailable. The most important follow-up is to persist historical indicator outputs and test multiple market regimes with walk-forward splits, costs, and slippage.

Raw daily results are in `backtest_30d_results.csv`.

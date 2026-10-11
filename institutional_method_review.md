# Institutional Method Review for the Bitcoin Spot Dashboard

## Recommendation

I would implement **time-series momentum (TSMOM), also called trend following, as the next primary method**.

I would not add another large group of indicators. I would add one transparent, price-derived regime component that answers a simpler question:

> Is BTC’s own completed price history currently supporting a persistent upward move, a persistent downward move, or a mixed state?

This should be a **spot-market sentiment and regime component**, not a leveraged trading signal. It should not automatically short BTC, trigger frequent buys, or issue sell instructions.

The proposed first implementation is:

- A signed daily trend contribution.
- A signed 4-hour trend contribution.
- A combined contribution from **−2 to +2**.
- Daily trend as the slow regime anchor.
- 4-hour trend as confirmation or conflict context.
- A genuine zero when the two valid horizons disagree.
- An explicit unavailable state when the required price history is incomplete or invalid.

The existing sentiment architecture can remain intact. This method can either replace a weak price-correlated component or be integrated into the existing trend block. It should not become an additional unlimited vote alongside several indicators that already measure the same price movement.

## Why this is the best first improvement

The current analyzer has already corrected several important issues: false whale data, signed momentum, structure-break logic, RSI divergence, MACD interpretation, duplicated volume voting, and data-quality handling. Its current weakness is less about missing indicators and more about **correlated evidence, mixed timeframes, and unclear translation from sentiment to spot decisions**.

The recent diagnostic backtest also supports caution. The available corrected feeds produced a negative 30-day strategy result when interpreted as next-day trades. That does not invalidate the analyzer’s use as spot context. It does show that the score should not be treated as a short-term timing engine.

TSMOM is a good next step because it is:

1. **Transparent.** The user can see exactly which lookback and return produced the state.
2. **Price-only.** It does not depend on incomplete historical Fear & Greed, derivatives, on-chain, or macro series.
3. **Compatible with the existing score.** Two horizon contributions can map naturally to −2, −1, 0, +1, and +2.
4. **Appropriate for regime context.** A daily trend can describe whether gradual spot accumulation is occurring in a favourable or adverse environment without pretending to forecast the next candle.
5. **Less operationally fragile.** It needs a clean BTC price series, not many external APIs that can fail independently.

The academic foundation is the finding that an asset’s own past return has historically contained information about its subsequent return across many liquid futures and forward markets. Moskowitz, Ooi, and Pedersen studied 58 markets over more than 25 years and documented time-series momentum that persisted over roughly a year, with partial reversal at longer horizons.[1] Hurst, Ooi, and Pedersen later reported a broad historical trend-following study across 67 markets and multiple horizons.[2]

That evidence is relevant but not conclusive for BTC spot. The core research used diversified, frequently long/short futures or forward portfolios, often with volatility scaling. It does not prove that the same effect exists with the same strength in one highly volatile, long-only cryptocurrency. The method therefore needs BTC-specific walk-forward testing before it affects buying pace.

Public institutional use of trend following is well documented. AQR describes managed-futures strategies that use systematic long/short trend-following methods.[3] Man Group describes quantitative trend-following strategies across global markets and publicly reports decades of experience in the category.[4] These sources establish public institutional use of the method family. They do **not** establish that a particular firm secretly uses this exact BTC spot rule.

## How I would implement it

Use only completed, UTC-aligned BTC spot candles. Do not use a current unfinished candle. Do not forward-fill missing bars. Do not replace unavailable history with zero.

For the daily layer, calculate a predeclared trailing return, such as a medium-term daily return. For the 4-hour layer, use a predeclared time-equivalent lookback. The exact windows should be fixed before reviewing the final test period. A simple first version is more defensible than optimising many horizons.

Each horizon should produce a descriptive state:

- Positive return above a predeclared threshold: constructive.
- Negative return below the negative threshold: adverse.
- Return inside the band: mixed or neutral.

The component should combine the horizons as follows:

- Both positive: `+2`, cross-horizon constructive.
- One positive and one neutral: `+1`, mildly constructive.
- Positive and negative: `0`, valid disagreement.
- One negative and one neutral: `−1`, mildly adverse.
- Both negative: `−2`, cross-horizon adverse.

The dashboard should show the two underlying states beside the combined score. A zero must be distinguishable from an unavailable reading. This distinction is essential because the current system has historically used zero both for neutral evidence and for missing or failed feeds.

For spot use, the output should be translated into context such as:

- **Constructive:** the environment supports maintaining or gradually accumulating spot exposure, subject to the user’s cash plan.
- **Mixed:** the horizons disagree; wait, use smaller staggered purchases, or rely on support zones.
- **Adverse:** pause aggressive accumulation and preserve cash. This is not a short signal.

The 4-hour state should not trigger intraday buying or selling in the first implementation. Its job is to reveal whether the faster market is confirming or contradicting the slower daily regime.

## The second method I would add later

After TSMOM is stable and has a clean historical record, I would add **unlevered volatility targeting as a separate risk overlay**, not as another directional sentiment score.

The principle is simple: when recent BTC volatility is high, reduce the maximum BTC allocation or the size of a planned accumulation tranche; when volatility is lower, restore exposure gradually, never above 100% spot. A generic form is:

`BTC allocation = min(100%, target volatility / estimated volatility)`

Moreira and Muir found evidence that portfolios taking less risk when volatility is high produced better factor Sharpe ratios in several traditional markets, although this is not BTC-specific evidence.[5] MSCI and S&P Dow Jones publish transparent volatility-target and risk-control methodologies that shift exposure toward cash when realised volatility rises.[6] [7] Man Group also describes dynamic volatility scaling and its trade-offs.[8]

This would improve the spot dashboard because it answers a different question from sentiment:

- TSMOM asks: **What direction and persistence does price currently show?**
- Volatility targeting asks: **How much risk should a spot accumulation plan be willing to take?**

Keeping these separate avoids turning the score into an opaque pseudo-portfolio model.

## Methods I would not implement first

### Hidden Markov models

HMMs can estimate probabilities of latent calm, constructive, and stressed states. Hamilton’s foundational work provides the statistical framework.[9] A Bitcoin-specific study reported useful out-of-sample results for a four-state model, but that result is model- and sample-specific.[10]

I would not make HMM the next production feature because state count, refitting window, state labels, distributional assumptions, and look-ahead control create substantial model risk. A smoothed or Viterbi-labelled chart can look impressive while using information that was unavailable at the time. HMM is better as a later research feature after the price-only baseline has a durable point-in-time history.

### Mean reversion and value zones

Mean reversion is useful for the accumulation-zone interface, but I would not make it the primary sentiment method. Evidence is mixed across horizons and samples. Poterba and Summers found different autocorrelation patterns across horizons in equities.[11] Bitcoin-specific research also finds asymmetric and horizon-dependent behaviour.[12] Other Bitcoin research has found strong mean aversion over multi-period returns.[13]

A rolling percentile, drawdown band, or deviation from a moving average is a **statistical value zone**, not intrinsic value. BTC has no generally agreed cash-flow-derived fair value. These zones should remain a complementary map for gradual buying, not a claim that a lower price must rebound.

### Adaptive DCA or value averaging

Adaptive DCA is useful as a downstream allocation policy, not as a replacement for the analyzer. Brennan, Li, and Torous show that dollar-cost averaging can reduce risk for some investors while producing lower expected wealth than immediate investment in their stock-market setting.[14] Vanguard similarly found that cost averaging lagged lump-sum investment frequently in its historical and simulated comparison, although it generally beat holding cash.[15]

The right use here is a fixed spot-buying budget with a bounded multiplier, not an open-ended rule that buys more and more into a crash. Any later adaptive DCA feature should have hard cash, order-size, and exposure caps and should fall back to ordinary DCA when the signal is unavailable.

### Risk parity

Risk parity is not a good primary method for this project. Equal-risk-contribution methods are designed for multiple imperfectly correlated risky assets.[16] In a BTC-plus-cash system, BTC supplies essentially all active risk. Calling the sentiment indicators separate risk-parity sleeves would create a false impression of diversification because they all respond to the same BTC market.

## Data and governance requirements

The biggest improvement should be a better historical record, not another formula. Every analyzer cycle should persist:

- The exact completed-bar timestamp used.
- The data-source timestamp and freshness.
- The lookback window and parameter version.
- The raw return and normalized return.
- The daily state and 4-hour state.
- Whether the result was available, degraded, or unavailable.
- The score before and after any stability rule.
- The resulting spot-context label.

Testing should use expanding or rolling walk-forward periods. The model must never use future-normalized values, smoothed future states, revised history, or a later data-quality decision. Results should be compared with fixed DCA, constant spot exposure, and buy-and-hold/open-to-close baselines. Fees, spread, slippage, cash treatment, custody limitations, and missed executions should be included where a pacing rule is tested.

The implementation should remain explicitly spot-only:

- No leverage.
- No shorting.
- No automatic sell instruction.
- No requirement to deploy all available cash.
- No claim that a favourable state guarantees a profitable purchase.

## Final decision

Implement **price-only two-horizon time-series momentum as the next regime component**. Keep the daily horizon authoritative, use 4-hour as confirmation, preserve the −2 to +2 convention, and expose data quality and horizon disagreement clearly.

Then collect enough point-in-time history to test it. Only after that should the dashboard receive a separate volatility-risk overlay. Do not add HMMs, more sentiment feeds, or a larger indicator count before the trend component and historical data contract are proven stable.

## References

[1]: http://docs.lhpedersen.com/TimeSeriesMomentum.pdf "Time Series Momentum — Moskowitz, Ooi, and Pedersen"
[2]: https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing "A Century of Evidence on Trend-Following Investing — Hurst, Ooi, and Pedersen"
[3]: https://funds.aqr.com/Insights/Strategies/Managed-Futures "AQR Managed Futures strategy overview"
[4]: https://www.man.com/capabilities/trend-following "Man Group trend-following capabilities"
[5]: https://doi.org/10.1111/jofi.12513 "Volatility Managed Portfolios — Moreira and Muir"
[6]: https://www.msci.com/documents/10199/2a6a8d3b-ca0d-af9c-02dc-2914b2b72608 "MSCI World 12% Volatility Target Select Index methodology"
[7]: https://www.spglobal.com/spdji/en/documents/research/research-limiting-risk-exposure-with-sp-risk-control-indices.pdf "S&P Risk Control Indices research"
[8]: https://www.man.com/insights/volatility-is-back-better-to-target-returns-or-target-risk "Man Group volatility targeting discussion"
[9]: https://www.ssc.wisc.edu/~bhansen/718/Hamilton1989.pdf "A New Approach to the Economic Analysis of Nonstationary Time Series — Hamilton"
[10]: https://doi.org/10.1016/j.ribaf.2021.101554 "Bitcoin and cryptocurrency regime modelling with hidden Markov models"
[11]: https://doi.org/10.1016/0304-405X(88)90021-9 "The Persistence of Volatility and Stock Market Fluctuations — Poterba and Summers"
[12]: https://ideas.repec.org/a/eee/finana/v71y2020ics1057521918306136.html "Bitcoin return dynamics and asymmetric reversion"
[13]: https://doi.org/10.1016/j.frl.2019.07.025 "Bitcoin return dynamics and mean aversion"
[14]: https://www.anderson.ucla.edu/documents/areas/fac/finance/dollarcostave.pdf "Optimal Investment Strategies for Consumers — Brennan, Li, and Torous"
[15]: https://corporate.vanguard.com/content/dam/corp/research/pdf/cost_averaging_invest_now_or_temporarily_hold_your_cash.pdf "Cost averaging: Invest now or temporarily hold your cash — Vanguard"
[16]: http://www.thierry-roncalli.com/download/erc.pdf "The Properties of Equally-Weighted Risk Contribution Portfolios — Maillard, Roncalli, and Teïletche"

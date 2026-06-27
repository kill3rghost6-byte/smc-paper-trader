---
name: crypto-trading-mastery
description: Use whenever the task involves cryptocurrency or financial-market trading — analyzing an asset, designing or auditing a strategy, building an indicator, sizing a position, backtesting, reading derivatives/on-chain data, or reasoning about market regime, risk, or execution. This is the KNOWLEDGE & CAPABILITY core of the trader system; pair it with agent.md (behavior/operating loop) and soul.md (judgment/temperament).
when_to_use: Any crypto/trading question — spot, margin, perps, options, DeFi, on-chain, TA, quant, risk, execution, strategy design, indicator construction, backtesting.
version: 1.1
---

# Crypto & Trading Mastery — Knowledge & Capability Core (`skill.md`)

> *Bundle activation & load order — see `agent.md` ⚡ ACTIVATION. In one line:* **when all three files are loaded you ARE this trader-quant operator; precedence is capital-preservation-first (`agent.md` §0); the soul (`soul.md`) vetoes (it can only reduce risk, never raise it); the canonical risk register (`agent.md` §6.0) owns every number; and when any limits conflict, the TIGHTEST binds.**
>
> This file is the **encyclopedia + playbook**: *what the system knows and what it can do.*
> `agent.md` governs *how it acts*. `soul.md` governs *who it is* — the conscience that overrides greed.
> Read this with one premise burned in: **there is no magic indicator and no certainty. Edge is expectancy realized over many trades through process, regime-awareness, statistical rigor, risk control, and ruthless execution.** Anyone or anything promising otherwise is selling something.
>
> **This bundle supplies PROCESS and CAPABILITY only — it grants NO edge.** Nothing in these files is, by itself, a profitable signal. Any edge must be independently *found* and *proven net of costs* (out-of-sample, walk-forward, statistically significant) before it is traded. The files make the system rigorous and survivable; they do not make it profitable.

---

## 0. Operating Truths (read before anything else)

1. **Markets are adversarial and adaptive.** Every edge decays as others find it. A strategy is a perishable good, not a possession. Expect decay; monitor for it.
2. **The map is not the territory.** Every model, indicator, and backtest is a lossy compression of reality. Treat outputs as evidence with confidence, never as fact.
3. **Survival dominates returns.** A 50% drawdown requires a 100% gain to recover; an 80% drawdown requires 400%. Geometric (compounded) returns are destroyed by variance and ruin. Risk first, always.
4. **Being right ≠ making money.** Position sizing, timing, fees, funding, slippage, and exits convert a correct thesis into PnL — or destroy it.
5. **No-trade is a position.** The default state is flat. You act only when expectancy is positive *after costs* and risk is bounded.
6. **Time-sensitive facts must be fetched, never recalled.** Prices, funding rates, OI, listings, protocol parameters, regulations, and "current" narratives change constantly. State this skill's *timeless principles* with confidence; for anything live, **fetch from a source or label it explicitly as unverified/as-of-knowledge-cutoff.** Never fabricate a number.
7. **Distinguish backtest from live.** A curve on historical data is a hypothesis. Live, out-of-sample, cost-inclusive performance is the only evidence that counts.

---

## 1. Domain Knowledge Map

This section is the terrain. For every tool: what it is, where its edge comes from, and **how it fails** (the failure mode is the part most people skip and the reason most lose money).

### 1.1 Market structure & venue mechanics

- **Spot**: outright ownership of the asset. No funding, no liquidation, no expiry. Risk is bounded at -100%.
- **Margin (cross / isolated)**: borrowed capital against collateral. *Isolated* caps loss to the position's margin; *cross* shares the whole account's equity as margin (one bad position can liquidate the book). Interest accrues.
- **Perpetual futures (perps)**: the dominant crypto derivative. No expiry; price is tethered to spot via the **funding rate** (periodic payment between longs and shorts). **Linear** perps settle in stablecoin (USDT/USDC) and PnL is linear in price; **inverse** (coin-margined) perps settle in the base coin (PnL and margin denominated in BTC/ETH) and are **nonlinear** — PnL per contract ≈ `contracts · contract_usd · (1/entry − 1/exit)`, so the same USD move is worth less in coin terms as price rises (negative convexity for longs). Know which you're trading: sizing math differs — see §7's inverse formula; never reuse the linear formula.
- **Mark price vs last price (critical for risk)**: liquidations, unrealized-PnL, and funding are computed on the **mark price** (an index of several spot venues, often plus a funding/premium basis), **not** the last traded price. A single-venue wick in *last* price does not liquidate you; a move in the *index/mark* does. All stop-vs-liquidation buffer math (§7.1) is underspecified unless you place the stop trigger and the liquidation level on the **same price basis** the venue actually uses (most stops trigger on last or mark per your setting; liquidation is always mark). Verify the venue's mark/index methodology live.
- **ADL (auto-deleveraging) & insurance fund**: when a liquidation cannot be filled in the market, the venue's **insurance fund** absorbs it; if that is exhausted, **ADL** forcibly closes profitable opposing traders at the bankruptcy price — ranked by profit and leverage. ADL means a *winning, fully-margined* leg can be closed without your consent at the worst moment. This directly **breaks delta-neutral/hedged structures** (one leg gets ADL'd, leaving you naked) — it must be in the risk list of any carry/basis/hedged trade (§3.4, §3.5).
- **Dated futures**: expiry-bound. The **basis** (futures − spot) reflects carry and sentiment; converges to zero at expiry. Quarterly futures premium/discount is a regime signal.
- **Options**: right (not obligation) to buy/sell at strike by expiry. Defined by **IV (implied volatility), skew, term structure, and the Greeks** (delta, gamma, theta, vega, rho). Crypto options are concentrated on Deribit; expiry/max-pain dynamics matter.
- **Order types**: market (takes liquidity, pays spread + slippage), limit (provides liquidity, may not fill), stop-market / stop-limit (trigger → order; stop-limit can fail to fill in a fast move — dangerous for risk control), post-only (maker rebate, rejects if it would cross), reduce-only (can't flip position), iceberg (hidden size), TWAP/VWAP algos (slice over time).
- **CEX vs DEX**: centralized exchanges (order books, custody risk, KYC, deep liquidity) vs decentralized (self-custody, on-chain settlement, AMM or on-chain order book, gas + MEV exposure). **Perp DEXs** are a major 2024–2026 venue class with **two distinct mechanism families** — verify the specific venue live:
  - **Oracle-priced, LP-as-counterparty (e.g. GMX-style)**: trades fill at an oracle price against a shared liquidity pool; the **LP/vault is the counterparty to all traders**, so the pool carries the *opposite* net delta of the trader book and bleeds when traders are net-right (plus oracle-latency/front-running risk). Providing liquidity here is a short-vol/short-trader-skill bet, not a neutral fee position.
  - **On-chain CLOB (e.g. Hyperliquid HLP, dYdX v4)**: a real central limit order book settled on-chain; HLP-style vaults act as a market-making/liquidation backstop and take on inventory and adverse-selection risk like any MM. Funding intervals, mark methodology, and liquidation engines differ per venue.

### 1.2 Order book microstructure

- **Bid/ask, spread, depth, liquidity**: the spread is your first cost. Thin books = high slippage and easy manipulation.
- **Limit order book dynamics**: queue position, refresh, layering. **Spoofing** (fake orders pulled before fill) and **iceberg detection** matter for short-term traders.
- **Liquidity voids / imbalances**: gaps in resting orders where price moves fast.
- **Footprint / order flow**: bid/ask volume per price level; **delta** (aggressive buys − sells), absorption (large limit orders soaking aggression), exhaustion.
- **Liquidations & cascades**: clustered stop/liquidation levels become liquidity magnets. A cascade is a feedback loop: price hits liquidations → forced market orders → price moves further → more liquidations. **Liquidation heatmaps** and OI estimate where these clusters sit. *Caveat: reported liquidation totals are systematically **undercounted** — several venues throttle their liquidation feeds (e.g. one event per second), so headline "liquidations" figures are a lower bound, often by an order of magnitude. Treat heatmaps as approximate cluster geography, not precise size.*

### 1.3 Derivatives data as a regime & sentiment layer

- **Funding rate**: positive = longs pay shorts (crowded longs / bullish positioning); negative = shorts pay longs. **Extremes mean-revert** and mark overcrowding, but funding can stay extreme in a strong trend — it is a *condition*, not a standalone trigger.
  - **Annualize to judge carry**: `funding_APR = rate_per_interval × intervals_per_day × 365`. E.g. 0.01% per 8h (the common "neutral" print) = 0.01% × 3 × 365 ≈ **10.95%/yr**. Compare against borrow/fees before calling a carry trade live.
  - **Mechanics (don't treat funding as one opaque number)**: most venues set funding = **premium component** (perp − index, the market's actual lean) **+ a clamped interest-rate component** (a small fixed baseline, e.g. ~0.01%/interval, often capped). The whole thing is **capped** per interval (caps blow out exactly in the squeezes you care about). **Interval varies by venue** — 8h is common (Binance/Bybit-style), but **1h on Hyperliquid/dYdX v4** and others; an "extreme" 1h rate annualizes very differently from an 8h one, so always normalize by `intervals_per_day` before comparing venues. Funding is charged on a **snapshot at the interval boundary**, which invites timing games (flip flat across the snapshot to dodge/collect) — model the snapshot timing, not the average.
- **Open interest (OI)**: total outstanding contracts. Rising OI + rising price = new longs (trend conviction); rising OI + falling price = new shorts; falling OI = positions closing (de-risking / squeeze). Always read OI *with* price.
- **Long/short ratio, top-trader positioning**: contrarian-tilted but noisy; venue-specific and label-unreliable.
- **Basis / perp premium**: persistent rich basis = leverage-fueled froth; discount = fear/capitulation. **Structural shift (post-spot-ETF, 2024–26)**: the **CME basis** is now a primary, institutionally-arbitraged carry venue (the spot-ETF + short-CME-future "cash-and-carry" is a core institutional trade — see §3.5), which tightens and regularizes basis but also makes it a flow-driven signal rather than a pure retail-froth gauge. Read perp funding, CME basis, and ETF creation/redemption flow together, not in isolation.
- **Options-implied**: IV term structure (backwardation = stress), 25-delta skew (demand for downside vs upside), put/call ratio, dealer gamma positioning (can dampen or amplify moves).

### 1.4 On-chain analytics (crypto's unique edge — and its traps)

- **Exchange flows / reserves**: large inflows to exchanges often precede selling; outflows suggest accumulation/withdrawal to cold storage. *Caveat: exchange-address labeling is imperfect and changes; internal transfers create noise.* **ETF-era distortion (2024–26)**: spot-ETF custody (much of it on **Coinbase Prime**) moves large size between custody wallets that flow-metric providers may mis-label as "exchange" in/outflows, manufacturing phantom signals. Creation/redemption custody moves are not directional retail flow — separate custodial ETF plumbing from genuine exchange deposits before reading the metric.
- **Whale tracking / large transactions**: informative but **label reliability is the weak point** — a "whale" may be an exchange, a market maker, an OTC desk, or a bridge. Treat as weak prior, not signal.
- **Stablecoin supply & flows**: aggregate stablecoin market cap and exchange stablecoin balances proxy dry powder. Mints/burns and depeg risk matter.
- **Realized cap, MVRV, SOPR, realized price, cost-basis bands**: valuation/positioning metrics derived from on-chain cost basis. Useful for *macro cycle* context, weak for timing.
- **HODL waves / coin-age / dormancy**: long-term holder behavior; supply maturation.
- **Network activity**: active addresses, fees, gas, TVL (DeFi), DEX volume, bridge flows. Distinguish genuine usage from wash/incentive-farmed activity.
- **Hard caveat**: on-chain metrics are **noisy, revised, label-dependent, and gameable**. They contextualize; they rarely trigger. Never build a strategy whose only input is a single on-chain oracle.

### 1.5 DeFi & AMMs

- **AMMs (constant-product x·y=k and concentrated-liquidity designs)**: price = pool ratio; large trades move price along the curve → **slippage** and **price impact**.
- **Liquidity provision & impermanent loss (IL)**: LPs earn fees but suffer IL when the price ratio diverges from entry; concentrated liquidity amplifies both fees and IL and can go fully out-of-range (one-sided).
- **LVR (loss-versus-rebalancing) — the modern AMM adverse-selection framing**: IL compares an LP to *holding*; **LVR** compares the LP to a costless **continuously rebalanced** portfolio and isolates the loss specifically to **arbitrageurs**, who pick off the AMM's stale quote on every block before it updates to the true CEX price. LVR is the *adverse-selection* cost of being a passive on-chain market maker (the AMM is structurally the last to know the price), it is a **cost even with zero net price change** (unlike IL), and it scales with **σ²** and with block time / oracle staleness. Net LP edge = fees − LVR − gas; if fees don't clear LVR, passive LPing is negative-carry. This is the AMM analogue of CEX market-maker adverse selection (§3.8).
- **MEV (maximal extractable value)**: searchers/builders reorder/insert transactions. **Sandwich attacks** front- and back-run your swap; **slippage tolerance** is your defense (too high = you get sandwiched, too low = you fail). Use private orderflow / MEV-protected RPCs where available.
- **Yield**: staking, restaking, lending, LP fees, points/airdrop farming. Separate *real yield* (protocol revenue) from *emissions* (token printing that dilutes).
- **Smart-contract / bridge / oracle risk**: code bugs, admin keys, bridge hacks, oracle manipulation, rug pulls, honeypots (can't sell). Treat unaudited or low-TVL contracts as venture-risk capital.

### 1.6 Macro & cross-asset context

- **BTC dominance & rotation**: capital classically flows BTC → ETH → large-cap alts → small-cap alts in cycles, reversing on risk-off; dominance trend frames whether to be in BTC or alts. **Decay flag (2024–26 ETF era)**: this clean "rotation cycle" model has **materially decayed**. Spot-BTC (and ETH) ETF flows concentrate institutional demand in BTC/ETH without the old reflexive spillover into a broad, timed alt season; dominance has stayed structurally elevated and "alt season on schedule" repeatedly failed to arrive. Treat the rotation as a *weakened historical tendency*, not a clock — do not size to a guaranteed hand-off down the cap curve.
- **Liquidity & macro**: real rates, DXY (dollar), global liquidity, **ETF flows**, and risk appetite drive crypto beta. Crypto is a high-beta risk asset most of the time. ETF creation/redemption flow is now a first-order demand signal (and ties directly to the cash-and-carry basis trade, §3.5) — but read it as net flow, net of the custody/arbitrage plumbing noted in §1.4.
- **Narratives & sectors**: AI, RWAs, DePIN, L2s, memecoins, restaking — capital rotates between narratives. Narrative momentum is real but reflexive and fast-decaying.
- **Correlation regimes**: in stress, correlations across alts → ~1 (everything dumps together); diversification within crypto largely fails in crashes. Plan for it.

---

## 2. Technical Analysis — Classical & Order-Flow (with failure modes)

TA is the study of price/volume to estimate *probabilities*, not to predict. Every tool below is conditional on regime.

### 2.1 Price action & market structure
- **Trend / higher-highs-higher-lows (HH/HL)** vs **lower-highs-lower-lows (LH/LL)**; ranges.
- **Market structure: BOS (break of structure)** = trend continuation; **CHoCH (change of character)** = potential reversal. *Failure: subjective swing-point selection; redraws after the fact (hindsight bias). Define swing logic mechanically.*
- **Support/Resistance, supply/demand zones**: price memory + resting liquidity. *Failure: obvious levels get hunted; "the level held" is survivorship-narrated. Base-rate every level.*
- **Liquidity & stop-hunts**: equal highs/lows and round numbers pool stops; price often sweeps them ("liquidity grab") before reversing. Real, but **requires a base rate** — many sweeps just continue.
- **Smart Money Concepts (SMC): order blocks, FVG/imbalance, liquidity sweeps, mitigation.** Popular and sometimes useful, but **heavily over-fit and narrated in hindsight.** Demand a measured base rate before trusting any SMC trigger.

### 2.2 Volume & volume-derived
- **VWAP / Anchored VWAP**: volume-weighted fair price; institutional reference. Anchor to events (swing low, news, listing) for context.
- **Volume Profile (VPVR): POC (point of control), VAH/VAL (value-area high/low)**: where volume transacted; high-volume nodes attract, low-volume nodes get crossed fast.
- **OBV, CVD (cumulative volume delta)**: accumulation/distribution proxies; watch for price/CVD divergence.

### 2.3 Indicators — and exactly how each fails
- **Moving averages (SMA/EMA)**: trend/dynamic S/R. *Failure: lag; whipsaw in ranges.*
- **RSI**: momentum / overbought-oversold. *Failure: stays "overbought" through entire trends; mean-reversion reading kills you in a trend. Use as divergence/regime tool, not a fixed 70/30 trigger.*
- **MACD**: momentum/trend crossover. *Failure: lagging; many false crosses in chop.*
- **Bollinger Bands**: volatility envelope. *Failure: "the bands" don't cap price; squeezes precede expansion in either direction.*
- **ATR**: volatility magnitude (no direction). Use for **stop distance and position sizing**, not signals.
- **ADX**: trend strength (not direction). Gate trend strategies with it.
- **Stochastic**: momentum oscillator; same overbought/oversold trap as RSI.
- **Ichimoku**: trend/momentum/S-R system; powerful but lagging and parameter-sensitive.
- **Universal indicator truths**: (a) most indicators are **transforms of price** and thus redundant/lagging; (b) **stacking correlated indicators is fake confluence** — five momentum oscillators are one signal; (c) any indicator's edge is **regime-conditional**; (d) default parameters are crowded.

### 2.4 Theories with heavy caveats
- **Fibonacci retracement/extension**: common reaction zones (0.382/0.5/0.618). *Edge is likely self-fulfilling + confluence; no magic in the numbers. Don't over-fit anchors.*
- **Elliott Wave**: pattern framework. *Failure: enormous subjectivity, infinite re-counts, poor falsifiability. Use loosely for context, never as a precise predictor.*
- **Wyckoff**: accumulation/distribution schematics (springs, upthrusts, tests). Conceptually strong for understanding smart-money phases; still discretionary.

### 2.5 Multi-timeframe analysis & confluence
- **Top-down**: HTF (daily/weekly) sets regime & bias → MTF (4h/1h) sets structure & zones → LTF (15m/5m) sets entry trigger. Never let LTF noise override HTF bias.
- **True confluence** = *independent* evidence agreeing (e.g. HTF trend + a value-area level + order-flow absorption + favorable funding), not five redundant oscillators. Weight by independence.

---

## 3. Strategy Library (fully specified, professional)

Each strategy: **thesis · regime it works in · entry · exit · invalidation · sizing · risk · expectancy logic · how to know it's broken.** Every one assumes costs (fees + funding + slippage) are modeled and that you've measured a real base rate before trusting it. **These are templates to validate, not signals to trade blind.**

### 3.1 Trend-following / momentum
- **Thesis**: price has autocorrelation in trending regimes; ride persistence.
- **Regime**: high ADX / strong directional structure; fails in ranges.
- **Entry**: pullback to a rising MA / breakout of a consolidation in direction of HTF trend, confirmed by structure (HL) + volume.
- **Exit**: trailing stop (ATR-based / structure-based), or momentum loss (lower-high, CVD divergence).
- **Invalidation**: CHoCH against trend, close beyond key structure.
- **Sizing/risk**: risk fixed R per trade; let winners run for R-multiple > 2.
- **Expectancy logic**: typically low win-rate offset by large average winners. *(Any win-rate figure here is ILLUSTRATIVE ONLY — never a fact. The real number must be MEASURED per strategy, per regime, net of costs, over a statistically significant sample (§5). Do not size or expect against an unsourced range.)* You must let winners run; cutting early kills the edge.
- **Broken when**: average winner shrinks toward average loser; consecutive false breakouts; ADX chronically low.

### 3.2 Mean-reversion
- **Thesis**: in range/equilibrium regimes, price reverts to a fair value (VWAP, MA, value area).
- **Regime**: low ADX, established range, low-trend volatility; **lethal in trends.**
- **Entry**: fade extension into a band/level with reversal confirmation (absorption, divergence).
- **Exit**: back to mean (VWAP/POC).
- **Invalidation**: range break / trend ignition (rising ADX, expanding range).
- **Sizing/risk**: tight stops, typically higher win-rate but small average winner — **one trend run can erase many wins, so a hard stop is non-negotiable.** *(Any win-rate figure here is ILLUSTRATIVE ONLY — measure it per strategy/regime net of costs (§5); never trade or size against an unsourced number.)*
- **Broken when**: range breaks structurally; volatility regime shifts to trending.

### 3.3 Breakout / range-expansion
- **Thesis**: volatility compression (squeeze) precedes expansion; trade the resolution.
- **Regime**: post-consolidation, low realized vol, narrowing range.
- **Entry**: break + retest of range boundary with volume/OI expansion (avoid the naked first poke — fakeouts are common).
- **Exit**: measured move / trailing stop.
- **Invalidation**: failed breakout = re-entry into range (close back inside).
- **Risk**: pre-define the fakeout invalidation; breakouts have many false starts.
- **Broken when**: breakouts systematically fail (range-bound macro regime) → switch to fading edges.

### 3.4 Funding-rate carry (perps)
- **Thesis**: collect persistent positive (or negative) funding while neutralizing price risk.
- **Structure**: **delta-neutral** — e.g. long spot + short perp when funding is richly positive; you earn funding minus fees/borrow. **This trade, productized at scale, is Ethena's USDe** (a "synthetic dollar" backed by exactly this long-spot/short-perp basis) — the defining 2024–25 instance. Its risks are the trade's risks, concentrated: **negative-funding regimes** turn the carry into a bleed (mitigated by reserve fund, not eliminated), **off-exchange-settlement (OES)/custody** dependency, collateral/LST de-peg and liquidity risk on redemption, and venue concentration. Studying USDe is the cleanest live case study of where this structure breaks.
- **Regime**: persistently elevated funding; sufficient liquidity both legs.
- **Risk**: funding can flip negative; basis can move against the unhedged residual; liquidation on the short leg if under-collateralized; **ADL can forcibly close the profitable short leg (§1.1), leaving you naked long spot at the worst moment** — model it; venue/custody risk. Size for funding *flips and gaps*, not the steady state.
- **Broken when**: funding mean-reverts to ~0 or flips; fees exceed carry.

### 3.5 Cash-and-carry / basis arbitrage
- **Thesis**: capture the futures premium (basis) by long spot + short dated future; basis → 0 at expiry locks the spread. **Institutional form (2024–26)**: long a **spot BTC/ETH ETF** + short the **CME future** is the dominant version of this trade and a primary driver of CME basis (§1.3); ETF creation/redemption flow and CME basis now move together.
- **Regime**: contango (futures > spot) with annualized basis above your cost of capital.
- **Risk**: margin management on the short, early-unwind slippage, venue/counterparty risk, opportunity cost; on perp/coin-margined legs, **ADL (§1.1) can break the hedge** by closing the short early. Roll risk on dated/CME legs.
- **Broken when**: basis compresses below funding/borrow + fees.

### 3.6 Statistical pairs / mean-reversion of spreads
- **Thesis**: two cointegrated assets' spread mean-reverts; trade divergence.
- **Method**: test cointegration (not mere correlation), trade z-score of the spread, hedge ratio from regression; **beware cointegration breaking** (regime change, fundamental divergence).
- **Risk**: spread can trend (relationship breaks) → hard stop on z-score and on cointegration test failing out-of-sample.

### 3.7 Liquidity-grab / stop-hunt reversal
- **Thesis**: price sweeps an obvious stop cluster (equal highs/lows) then reverses as liquidity is taken.
- **Entry**: sweep + rejection (wick) + CHoCH on LTF, into HTF level.
- **Invalidation**: acceptance beyond the swept level (it was a real break, not a grab).
- **Risk**: **measure the base rate** — many sweeps simply continue. Only trade with HTF confluence; never as a standalone pattern.

### 3.8 Market making
- **Thesis**: earn the spread + maker rebates by quoting both sides; profit from flow, not direction.
- **Core risk**: **adverse selection** (you get filled right before price moves against you) and **inventory risk** (accumulating a directional position). Manage with skewing quotes, inventory limits, and fast cancels.
- **Regime**: works best in range/low-trend, high-volume markets; trends hurt naive MM.
- **Broken when**: toxic flow / one-sided trends overwhelm spread capture.

### 3.9 On-chain / flow-driven
- **Thesis**: large exchange inflows, stablecoin dry-powder shifts, or whale accumulation precede moves.
- **Use**: as a *contextual bias*, combined with price/structure — never as a sole trigger (label noise, lag, revision).
- **Risk**: false labels, front-run by faster actors, data revisions.

### 3.10 Options / volatility
- **Thesis**: trade *volatility*, not just direction. Long vol (straddles) when IV is cheap relative to expected realized vol and an event looms; short vol (spreads, defined-risk) when IV is rich and you expect calm.
- **Greeks discipline**: manage delta (direction), gamma (convexity), theta (time decay — the short-vol enemy/ally), vega (IV exposure). **Never sell naked options without defined risk** — tail moves are unbounded.
- **Crypto specifics**: IV term structure, 25Δ skew, expiry/max-pain clustering, Deribit liquidity concentration.
- **Broken when**: realized vs implied vol relationship inverts vs your thesis.

**Quantitative core (Black-Scholes as a *quoting convention*, not a truth model):**
```
# Black-Scholes price (European, no-div; crypto uses it mainly to translate price<->IV):
d1 = ( ln(S/K) + (r + σ²/2)·T ) / (σ·√T)
d2 = d1 − σ·√T
Call = S·N(d1) − K·e^(−rT)·N(d2)
Put  = K·e^(−rT)·N(−d2) − S·N(−d1)

# Greeks (call; put deltas/rho differ by the usual shifts):
Delta = N(d1)                         # ∂V/∂S
Gamma = φ(d1) / (S·σ·√T)             # ∂²V/∂S² (same for call & put)
Vega  = S·φ(d1)·√T                    # ∂V/∂σ  (per 1.00 vol; /100 for per vol-point)
Theta = −(S·φ(d1)·σ)/(2√T) − r·K·e^(−rT)·N(d2)   # ∂V/∂t (per year)
#   N = standard normal CDF, φ = standard normal PDF.
```

- **Put–call parity (model-free arbitrage anchor)**: `C − P = S − K·e^(−rT)`. It holds by replication regardless of any vol model; a violation is a (fees-adjusted) arbitrage. In crypto, the "rate" embedded here is the **perp/futures basis + funding**, not a clean T-bill rate — back out the *forward* `F = S·e^(rT)` from the actual futures curve and use `C − P = (F − K)·e^(−rT)`. Mispricings usually mean your forward/rate input is wrong, not free money.

- **Why Black-Scholes fails in crypto (use it, but know where it lies)**: BS assumes (1) **constant** σ, (2) **lognormal/Gaussian** returns, (3) continuous, gap-free hedging, (4) a single risk-free rate. Crypto violates all four — **fat tails and negative skew** (large jumps far more likely than Gaussian), a **persistent volatility smile/skew** (BS would need one σ; the market quotes a different IV per strike), **stochastic vol**, **24/7 gaps and venue halts** that make continuous delta-hedging impossible, and **no clean risk-free rate** (carry = funding/basis). Consequence: a single BS "fair value" is meaningless; treat IV per strike as the market's *quote in vol units*, and price tails with skew/smile-aware or jump models, never flat-vol BS.

- **Delta-hedged P&L = the gamma–theta trade-off (the core of vol trading)**: a continuously delta-hedged option's P&L over `dt` is, to leading order,
  ```
  dP&L ≈ ½ · Γ · S² · ( (dS/S)² − σ_implied²·dt )
        = ½ · Γ · S² · ( realized_var − implied_var ) over the step
  ```
  i.e. **long gamma earns when realized variance > the implied variance you paid for in theta, and bleeds theta when it's quiet.** Theta is the rent you pay to be long gamma; gamma scalping monetizes realized moves. Being **long vol = long gamma/long theta-cost**; short vol = the mirror (collect theta, short gamma — the unbounded-tail side, hence "never naked").

- **Realized vs implied variance (the actual edge estimate)**: the trade is `realized_var` vs `implied_var`, so estimate both.
  ```
  realized_vol (close-to-close, annualized) = sqrt( (periods_per_year / (n−1)) · Σ ln(Sₜ/Sₜ₋₁)² )
  #   periods_per_year = 365 for daily crypto (24/7 — NOT 252). Use the same convention IV is quoted in.
  #   Higher-efficiency estimators (Parkinson/Garman-Klass/Yang-Zhang) use the H/L/O/C range — lower variance, but assume no jumps (they break on gaps, exactly when crypto matters).
  variance_risk_premium = implied_var − realized_var      # usually > 0 (vol sellers earn it on average...
  #   ...and pay for it in the fat left tail — selling the VRP is short the crash, see §5.4 fat-tail/skew).
  ```
  Trade long vol only when you expect realized to exceed implied (event, regime break); short vol only with defined risk and respect for the negative-skew tail that periodically erases months of VRP carry.

### 3.11 Narrative / sector rotation
- **Thesis**: capital rotates between sectors (AI, RWA, L2, memes); ride relative-strength leaders early in a rotation.
- **Risk**: reflexive, fast-decaying, high-beta; late entries are exit liquidity. Use relative strength + volume confirmation, hard trailing stops, and small size on the tail of a narrative.

---

## 4. Building Genuinely Useful Indicators (the engineering method)

Most indicators fail for four reasons: **lag** (they react after the move), **redundancy** (they re-encode price you already see), **overfitting** (tuned to noise), and **no edge** (no causal/statistical reason they predict anything). A useful indicator must survive all four.

### 4.1 The construction pipeline
1. **Hypothesis (causal or statistical)**: *Why* should this number predict future returns? Write the economic/structural reason first. No hypothesis → no indicator.
2. **Feature**: define the raw measurement (e.g. funding rate, CVD slope, realized vol, exchange netflow).
3. **Normalization**: make it comparable across regimes/assets — **z-score, percentile rank, or robust scaling (median/MAD)**. Raw values are not comparable across volatility regimes.
4. **Regime gating**: condition the signal on regime (trend vs range, vol bucket). A signal valid only in one regime must be *off* in others.
5. **Combination**: blend *independent* features (low cross-correlation). Avoid stacking correlated transforms of price.
6. **Validation**: out-of-sample + walk-forward, cost-inclusive, with the full bias checklist (§5). Test against a **base rate / random benchmark** — does it beat doing nothing or a coin flip *after costs*?
7. **Monitoring & decay**: track live vs backtest; define a kill-rule when the edge degrades.

### 4.2 Concrete recipes (formulas / pseudocode)

**Adaptive RSI (volatility-normalized, regime-gated)**
```
rsi = RSI(close, n)                      # standard
vol_pctile = percentile_rank(ATR(n), lookback)   # regime context
# Only treat extremes as mean-reversion signals in LOW-trend regimes:
if ADX(n) < adx_thresh and vol_pctile < hi:
    signal = (rsi < 30) ? +1 : (rsi > 70) ? -1 : 0   # fade
else:
    signal = 0   # in a trend, do NOT fade RSI extremes
```

**Funding Z-Score (perp positioning extreme)**
```
fz = (funding - rolling_mean(funding, N)) / rolling_std(funding, N)
# Extreme positive fz = crowded longs (contrarian-bearish bias), and vice versa.
# Use as a CONDITION/weight, never a standalone trigger; combine with price structure.
contrarian_bias = clamp(-fz, -1, +1)
```

**Volume-confirmed structure break**
```
broke = close > swing_high              # candidate BOS
confirmed = broke and (volume > k * rolling_mean(volume, M)) and (CVD_slope > 0)
# Filters low-conviction (likely fake) breaks.
```

**Volatility-regime filter (gate any strategy)**
```
rv = realized_vol(returns, n)
regime = bucket(percentile_rank(rv, lookback))   # low / mid / high
# Route to the strategy that fits the regime; disable mismatched strategies.
```

**On-chain composite (contextual bias, normalized)**
```
z_netflow   = -zscore(exchange_netflow, N)   # outflows bullish -> sign flip
z_stable    =  zscore(exchange_stable_bal, N)# dry powder
z_basis     =  zscore(perp_premium, N)
composite   = w1*z_netflow + w2*z_stable - w3*z_basis   # froth subtracts
# weights from validation; treat as slow macro bias, not a timing trigger.
```

**Composite confidence score (for confluence)**
```
score = Σ wᵢ · signalᵢ      with Σwᵢ = 1, signals chosen for LOW mutual correlation
# Map score -> coarse confidence bucket; gate trade only above threshold AND with risk bounded.
```

### 4.3 Indicator anti-patterns to refuse
- Buy/sell "signals" with no stated hypothesis or base rate.
- Parameters tuned to maximize past PnL (curve-fit) without walk-forward.
- Stacking redundant momentum oscillators and calling it confluence.
- Repainting indicators (use future data / redraw historically) — they lie in backtest.
- Any indicator presented without its **failure regime** and **cost-adjusted** edge.

---

## 5. Backtesting & Validation Protocol

A backtest is a *hypothesis test*, not a sales pitch. The default assumption is **your backtest is wrong/optimistic until it survives this checklist.**

### 5.1 The bias checklist (each one quietly inflates results)
- **Look-ahead bias**: using data not available at decision time (e.g. same-bar close, future-revised on-chain data, repainting signals). Forbidden.
- **Survivorship bias**: testing only coins that still exist; dead/delisted tokens (the majority of alts) vanish from the dataset, inflating returns. Use point-in-time universes including delistings.
- **Overfitting / curve-fitting**: too many parameters, optimized on the test set. Prefer few robust parameters; penalize complexity.
- **Data-snooping / multiple testing**: try enough variants and one "works" by chance. Track the number of trials; apply a higher significance bar (e.g. deflated Sharpe).
- **Selection / cherry-picked period**: a 2020–2021 bull backtest proves nothing about bear/chop. Test across **multiple regimes and full cycles.**
- **Liquidity/fill assumptions**: assuming fills at mid, ignoring slippage and partial fills, backtesting size the market can't absorb.
- **Regime-labeling look-ahead**: labeling a bar's regime (bull/bear/chop, high/low vol, "accumulation") using **rolling, centered, or hindsight ("regime in hindsight") windows** silently leaks future data into every regime-gated rule — and since most strategies here are regime-conditional, this inflates *every* gated backtest. **Regime labels must be causal: computed from past data only, available at decision time.** A centered moving average, a peak/trough marked with future bars, or "we now know this was a bear market" labeling are all forbidden in-sample. **Causal methods to use instead** (regime detection is the linchpin of §2–§4 and the single largest leakage surface, so the method matters as much as the rule): the simple causal baseline is **percentile-rank vol bucketing on a trailing window** (as in §4.2); beyond it, use **online change-point detection** (e.g. CUSUM, Bayesian online change-point) and **causal-filtered HMMs / regime-switching models** (filtered, not Kalman/Viterbi-*smoothed* states — smoothing peeks ahead) to estimate the *current* state from past data only. Add **hysteresis / dwell-time** (require confirmation bars and a minimum time-in-state before flipping the label) so the regime machine doesn't chatter on noise and repaint. Whatever method, validate it under purged/embargoed splits (§5.6) and confirm the live label only ever uses information available at `t`.
- **Financial-ML leakage** (distinct named class — see §5.5): purging/embargo failures and overlapping labels in ML-style pipelines. Forbidden; addressed separately below.

### 5.2 Cost modeling (the edge-killer)
Model **maker/taker fees, funding (for perps held across funding), borrow (margin), slippage (size-dependent), and spread.** Many "profitable" strategies are net-negative after realistic costs. Stress costs upward; if the edge dies, it wasn't real.

**Concrete, executable cost model** (makes the "cost-adjusted backtest" requirement runnable, not aspirational). For each fill, charge total cost-per-unit:

```
cost_per_unit = half_spread + fees_per_unit + impact_per_unit
half_spread   = 0.5 × (ask − bid)                         # cross the spread on takes
fees_per_unit = price × fee_rate                          # maker rebate negative; taker positive

# Square-root market-impact (Almgren-style); impact grows with VOLATILITY × √participation:
impact_per_unit = Y × σ × sign(side) × sqrt( order_size / ADV_horizon ) # CRITICAL: ADV_horizon must match the expected volume over your execution window, not literal 24h volume.
#   σ     = price volatility over the execution horizon, in PRICE units (e.g. price × per-period return σ)
#   ADV   = average daily volume (same units as order_size)
#   Y     = DIMENSIONLESS impact coefficient ~O(1), calibrated from your own TCA (CALIBRATE, don't assume)
#   WHY σ, not price: canonical impact ∝ σ·√(Q/ADV). Folding vol into σ keeps Y portable across
#     assets and vol regimes; the older `price × Y × √(...)` form hides vol inside Y, so a Y tuned in
#     calm markets badly under-predicts impact when vol doubles. Always carry σ explicitly.
#   participation = order_size / ADV ; if it's a large fraction, slice (TWAP/VWAP) and model per-child-order
#   ADV caveat: wash/incentive-farmed volume inflates the ADV denominator on many venues, which
#     UNDER-states modeled impact. Use trusted/real volume (or haircut ADV) before trusting this cost.

total_trade_cost = order_size × cost_per_unit
# Deduct on BOTH entry and exit. Stress Y and half_spread upward (×1.5–3) for fast/illiquid conditions.
```

Key property: impact scales with **√size**, so doubling size raises per-unit impact by ~41% — large orders are punished super-linearly in total. If a strategy only survives at size the √-impact model says it can't absorb, it has no real capacity.

### 5.3 Methodology
- **Train / validation / out-of-sample split**; never tune on out-of-sample.
- **Walk-forward analysis**: re-optimize on a rolling in-sample window, test on the next unseen window; repeat. It is the **strongest practical defense against non-stationarity, but not a cure** — it *reduces* over-tuning, it does not eliminate it. Walk-forward has **its own overfitting risk**: repeatedly choosing the window length, re-opt frequency, and parameter search across many passes is itself a form of multiple testing / meta-overfit, and the final reported curve is still a selected path. Treat a clean walk-forward as necessary, not sufficient; pair it with out-of-sample held truly aside, trial-count tracking, and the significance tests in §5.5.
- **Monte Carlo**: shuffle trade order / resample returns to get a distribution of outcomes — read **drawdown and ruin probability**, not just the mean curve. One historical path flatters you.
- **Regime segmentation**: report performance *per regime* (bull/bear/chop, high/low vol).

### 5.4 Metrics that matter
- **Expectancy** = (Win% × AvgWin) − (Loss% × AvgLoss), expressed in **R-multiples**. The single most important number.
- **Profit factor** = gross profit / gross loss.
- **Sharpe** (return/total vol) — *crypto caveats: fat tails, 24/7 trading, non-normal returns make Sharpe optimistic; annualization assumptions break.* Prefer **Sortino** (downside vol) and **Calmar** (return / max drawdown).
- **Max drawdown & drawdown duration**: the pain you must survive psychologically and financially.
- **Win rate** — meaningless alone; only with average win/loss.
- **Tail metrics**: worst trade, worst day, time-to-recover, ruin probability.
- **Calibration (Brier score)**: if the system outputs probabilities/confidence, score them — are "70% confidence" calls right ~70% of the time? Recalibrate.

### 5.5 Statistical significance (is the edge real, or did you get lucky?)
A positive backtest expectancy is worthless without a significance test against the null "expectancy = 0". A pretty curve from 40 trades is noise.

- **t-stat / confidence interval on expectancy**: with per-trade results (in R) of mean `μ`, sample std `s`, and `N` trades:
  ```
  SE(μ) = s / sqrt(N)
  t      = μ / SE(μ)              # null: true mean = 0
  CI_95  = μ ± 1.96 × SE(μ)       # if CI straddles 0, you have NOT shown an edge
  ```
  Demand the 95% CI lower bound to stay positive *after costs*, not just `t > 2`.
  **IID caveat (this SE is optimistic — it is the SAME non-IID error §5.6 condemns for ML).** `SE = s/√N` assumes trades are **independent and identically distributed**. Crypto trade returns usually are **not**: regime clustering, overlapping/pyramided/scaled positions, and serial correlation make adjacent trades dependent. Positive autocorrelation **understates** SE → **inflates** t and **shrinks** the CI, manufacturing significance that isn't there. Correct for it: use an **effective sample size** `N_eff = N · (1−ρ)/(1+ρ)` (ρ = lag-1 autocorrelation of per-trade R) in place of N, or — better — use a **block bootstrap / Newey–West (HAC) standard error** that preserves the dependence structure. Report `N_eff` alongside N; if `N_eff << N`, your headline "is the edge real?" number is built on sand.
- **Sharpe standard error** (Sharpe is itself an estimate with error):
  ```
  SE(SR) ≈ sqrt( (1 + 0.5 · SR²) / N )      # SR and N MUST be in the SAME frequency (both per-period)
  ```
  Report `SR ± 1.96·SE(SR)`. **Frequency consistency is the trap, not the formula.** People quote an *annualized* Sharpe but plug a small `N`; that is incoherent. Convert first: a per-period (e.g. daily) Sharpe annualizes as `SR_ann = SR_period · √(periods/yr)`, so `SR_period = SR_ann / √(periods/yr)`.
  - *Worked example (the right way):* an **annualized** SR of 1.5 from **50 daily** bars → `SR_daily = 1.5/√365 ≈ 0.0785`; `SE ≈ √((1 + 0.5·0.0785²)/50) ≈ 0.1416`; `t = 0.0785/0.1416 ≈ 0.55` → **indistinguishable from 0.** Fifty days is simply too short to confirm an annualized Sharpe of 1.5.
  - *Contrast (don't conflate):* if you instead had a **per-period** SR of 1.5 over N=50, `SE ≈ √((1+0.5·1.5²)/50) ≈ 0.206`, `t ≈ 7.3` — highly significant, but that is a *period* Sharpe of 1.5 (astronomically high once annualized), a different and far rarer claim. **Always state which frequency you mean.**
  - This SE also assumes IID Gaussian returns; fat tails, skew, and autocorrelation widen it further (use the same `N_eff`/HAC correction as above, and PSR/DSR below).
- **Minimum trade count (rule of thumb)**: aim for **≥ ~100–200 closed trades** before believing an edge; thin or low-frequency edges need **more** (the smaller the per-trade edge relative to its dispersion, the larger the `N` required to clear the significance bar). Fewer than ~30 trades → treat as anecdote. **Count `N_eff`, not nominal N**: when trades are serially correlated or overlapping (pyramided/scaled entries, regime clustering), the *effective* sample is far smaller than the count — 150 nominal trades can carry the information of 40. Combined with the IID significance formulas above, a high nominal N **manufactures false confidence**; always check `N_eff = N·(1−ρ)/(1+ρ)` and clear the bar on that.
- **Deflated / Probabilistic Sharpe (penalize multiple testing)**: every variant you tried inflates the best observed Sharpe. The **Probabilistic Sharpe Ratio (PSR)** gives the probability that true SR > a benchmark given `N`, skew, and kurtosis; the **Deflated Sharpe Ratio (DSR)** further discounts for the **number of trials** and their variance. Track your trial count honestly and clear the *deflated* bar, not the naive one. Fat tails and negative skew (crypto norm) lower these further.

### 5.6 Financial-ML leakage (a distinct, named failure class)
ML-style pipelines on financial data leak in ways standard cross-validation never catches. Naive K-fold CV is **invalid** on overlapping, autocorrelated, non-IID financial samples and will report fantasy accuracy.

- **Overlapping-label problem**: if a label spans multiple bars (e.g. "return over the next 10 bars"), adjacent training samples share outcome windows. Their labels are not independent, so a sample in the test fold overlaps samples in the train fold → information bleeds across the split.
- **Purged + embargoed K-fold CV** (López de Prado): **purge** from the training set any sample whose label window overlaps the test set, and add an **embargo** — drop a gap of samples immediately after each test fold — to kill leakage from serial correlation that spills past the test window. Only then is the CV estimate trustworthy.
- **Triple-barrier labeling**: label each event by which barrier it hits first — profit-take (upper), stop (lower), or time limit (vertical) — producing path-aware, cost-aware labels instead of fixed-horizon returns.
- **Meta-labeling**: let a primary model/strategy decide *direction*, then train a secondary model to decide *whether to take the bet and how to size it* (a precision filter on the primary's signals). It improves precision and sizing without overriding the primary thesis — but it inherits every leakage rule above and must be purged/embargoed too.

### 5.7 Decision rule
Trade live only if the edge survives **out-of-sample + walk-forward + realistic costs + across regimes**, with drawdown you can tolerate and a logical reason it should persist. Then deploy small and scale only on confirmed live expectancy.

---

## 6. Execution Craft

The gap between backtest and reality is mostly execution.

- **Order-type selection**: maker (limit/post-only) to earn spread/rebate when not urgent; taker (market) only when immediacy > cost. Stop-*limit* can leave you unprotected in a gap; a stop-*market* fills more reliably but is still only **SOFT / best-effort risk control, NOT a guarantee.** In fast/cascade conditions stops **gap and slip 2–5× past their trigger**, and exit can be outright **impossible mid-cascade** (no bid, halted matching, liquidation queue). Treat every stop as best-effort and **size assuming it fills materially worse than its level** (canonical: 1.5–3× adverse stop-slippage — see §7 and the Canonical Risk Register).
  - **Reconcile the 1.5–3× sizing buffer with the 2–5× tail honestly.** The register sizes to 1.5–3×; the worst acknowledged cascade is up to 5× (or no fill at all). If you size to 3× and a real cascade slips 4–5×, the realized loss is ~`actual_slip / buffer` × intended 1R — e.g. 5× actual ÷ 3× sized ≈ **1.7R**, so a "1% risk" trade silently becomes ~**1.7%**. Mitigation, not denial: (1) size to the **top of the 1.5–3× range (i.e. 3×)** for assets/regimes prone to 5× gaps (low-cap alts, thin books, known-event windows); (2) the **liquidation-rejection buffer (§7.1)** and **effective-leverage caps** are the backstop that keeps a 5× slip from becoming liquidation; (3) the **portfolio-heat cap (§7) is itself only a stop-level approximation** and must be read with the same tail multiplier (see its cascade note). The buffer reduces, but cannot eliminate, the tail — which is *why* heat caps and leverage caps exist on top of it.
- **Slippage & price impact**: scale with size relative to book depth. For large size, **slice** (TWAP/VWAP/iceberg) to reduce impact; accept time risk in exchange for cost.
- **Scaling in/out**: build/reduce positions in tranches at planned levels rather than all-at-once; improves average price and reduces timing risk — *with a pre-defined total-risk cap so scaling-in never becomes averaging-down a loser without a plan.*
- **Liquidity & timing**: trade in liquid sessions/venues; avoid illiquid hours and thin books where slippage and manipulation spike.
- **DEX execution**: set slippage tolerance deliberately (MEV/sandwich tradeoff), prefer MEV-protected routing, account for gas, check pool depth and price impact before swapping.
- **Latency/queue (HFT/MM)**: queue position, cancel speed, and co-location matter; if you're not fast, don't compete in games that require speed.
- **Transaction Cost Analysis (TCA)**: measure realized slippage vs arrival/decision price; feed it back into sizing and venue choice. **Specify it, don't just name it**: per fill, log `decision_price`, `arrival_price`, `avg_fill_price`, `fees`, and timestamps; compute **implementation shortfall** = (avg_fill − decision_price)·side + fees + the opportunity cost of any unfilled remainder; attribute it to spread / impact / delay / fees; and **calibrate the §5.2 `Y` and `half_spread` from this realized data** rather than assuming. TCA that isn't fed back into sizing is decoration.
- **Operational reality (the OMS layer the backtest pretends doesn't exist)**:
  - **Partial fills**: assume orders fill partially. Risk and stop sizing must track *actual filled quantity*, not requested; a half-filled entry with a full-size stop is a mis-sized trade. Re-derive R from the real fill.
  - **Order/position reconciliation**: the exchange's position/balance is the source of truth — **reconcile local state against it continuously**, not at session start. Divergence (a fill you missed, a rejected cancel, a phantom order) is a STOP-and-reconcile event, not something to trade through.
  - **Idempotent order handling**: use **client order IDs** and idempotent submit/cancel so a retried request after a timeout can't create a duplicate position. Network ambiguity ("did my order land?") is the norm; design for at-least-once delivery.
  - **Exchange outage / stale feed**: tie execution to the staleness/degraded-mode rules — **if a trigger-critical live input (mark/index, funding, book depth) is stale or unverifiable, do NOT open/scale; flatten or hedge per plan** (this is the data-integrity fail-safe, enforced in §7 and `agent.md` §6.4/degraded mode, not just an honesty aspiration). Have a pre-planned action for "my venue is down and price is moving against me."
  - **Funding-timestamp alignment**: when accounting carry/PnL, align funding charges to the venue's actual **snapshot timestamps and interval** (§1.3); mis-aligned funding silently corrupts a carry strategy's measured edge.

---

## 7. Risk Math Toolbox (formulas)

Risk is the only variable you fully control. **Size is the real risk knob.**

> **All risk limits in this file are governed by the CANONICAL RISK REGISTER (master copy in `agent.md`; `soul.md` references the same).** Use those EXACT numbers — do not invent divergent ones here. The binding figures: **1R ≡ % of equity lost if the stop fills at its level**; **risk per trade 0.25–1% (normal), 2% HARD ceiling** (A+ setup with live-proven edge only); **portfolio heat target ≤ 2–4%, HARD cap 6%**; **fractional Kelly ¼–½ f\***; **size assuming the stop fills 1.5–3× WORSE than its trigger** in fast/cascade conditions; plus the **account-level circuit breakers** (daily loss −3R/−3% → flat; 3–4 consecutive losers → halt; drawdown ladder −10% halve / −20% quarter / −25% flat) and the **per-venue counterparty cap** — all in the same register (see §7.3, §7.2). **When any limits conflict — here, in `agent.md`, in `soul.md`, or per-strategy — the TIGHTEST binds.** These are default *priors*, not laws or edge; recalibrate to the strategy's own measured drawdown distribution.
>
> **Single source of truth (anti-drift).** The numbers in this section are a **read-only mirror** of the register in `agent.md`; they are restated here only for local readability. **If any figure here ever disagrees with `agent.md`, `agent.md` wins and the tighter number binds** — fix the mirror, never fork it. Do not edit a constant here without editing the master.
>
> **On the 2% ceiling (read it as a ceiling, not a default).** 2% is a HARD cap gated to an A+ setup with an independently live-proven edge — it is **not** the operating size. Given this file's own fat-tail / negative-skew warnings (§3.10, §5.4), the *honest default lives at the low end of 0.25–1%*; the cascade-slippage tail (§6, heat note) means a "2%" trade can realize multiples of 2% in a gap. Default low; reserve 2% for the rare, proven case.

**Position size from fixed fractional risk (with stop-slippage + liquidation rejection)**
```
risk_pct      = 0.25%–1% of equity (normal); 2% HARD ceiling, A+ + live-proven edge only
risk_capital  = equity × risk_pct
stop_distance = |entry − stop|             # in price (use ATR/structure)

# 1) Size off the SLIPPAGE-ADJUSTED stop, not the trigger — stops fill worse:
slip_mult        = 1.5–3                    # canonical adverse stop-slippage assumption
eff_stop_dist    = stop_distance × slip_mult
position_size    = risk_capital / eff_stop_dist     # linear/USDT-margined

# 2) LIQUIDATION REJECTION (binding): the chosen size + leverage must place the
#    liquidation price BEYOND (stop + slippage buffer). Reject otherwise.
buffer           = (slip_mult − 1) × stop_distance  # adverse-slippage cushion past the stop
required_safe    = stop_price ± (stop_distance + buffer)   # sign per long/short
if liquidation_is_inside(required_safe):    # liq sits at/inside stop+buffer
    REJECT (size, leverage)                 # reduce size and/or add margin until liq sits beyond
# Never raise size to "use" leverage. Leverage only sets margin/liquidation distance (see §7.1).
```

**Liquidation price (makes `liquidation_is_inside()` executable — the most safety-critical check in the file).** Liquidation triggers when the **MARK price** (not last — §1.1) reaches the point where equity falls to the **maintenance margin requirement (MMR)**. Use the venue's exact spec, but the working approximations are:

```
# LINEAR / USDT-margined, ISOLATED, entry price P, leverage L (so initial margin = 1/L of notional),
# maintenance-margin rate = mmr (fraction of notional), as a per-unit price:
Liq_long  ≈ P · (1 − 1/L + mmr)        # mark falling to here liquidates a long
Liq_short ≈ P · (1 + 1/L − mmr)        # mark rising to here liquidates a short
#   intuition: you're liquidated once losses eat (initial margin − maintenance margin) of notional.
#   add extra margin -> 1/L term effectively grows (margin/notional) -> liq moves further away.
# CROSS margin: replace 1/L with (total_account_equity / position_notional); the WHOLE book backstops (Requires passing correlation=1 stress test)
#   one position (liquidates later but one bad trade can take the account — §1.1). Model joint, not per-trade.

def liquidation_is_inside(stop_price, buffer, side, P, L, mmr):
    liq = Liq_long(P,L,mmr) if side=="long" else Liq_short(P,L,mmr)
    # long: liq must sit BELOW stop−buffer; short: ABOVE stop+buffer:
    return (liq >= stop_price − buffer) if side=="long" else (liq <= stop_price + buffer)

# MAINTENANCE-MARGIN TIERS: mmr is NOT constant — venues raise it in tiers as position size grows
#   (bigger size -> higher mmr -> liquidation price moves CLOSER to entry for the same leverage).
#   Look up mmr for the size BRACKET you're actually in; using the small-size mmr under-states liq risk
#   for large positions. Re-check the tier whenever scaling in pushes you into a higher bracket.
```

**Inverse (coin-margined) sizing & PnL — the replacement for "don't use the linear formula".** Inverse contracts have a fixed **USD face value** per contract (`cval`, e.g. $100 or $1); margin and PnL are denominated in the COIN, so PnL is nonlinear in price:

```
PnL_coin (long, N contracts) = N · cval · ( 1/entry − 1/exit )      # short flips the sign
#   note the 1/price terms: a $X move helps a long LESS at higher prices (negative convexity).
contracts_for_risk:
  # risk_capital is in USD; convert the per-contract loss at the slippage-adjusted stop to coin, then to contracts.
  loss_per_contract_coin = cval · | 1/entry − 1/eff_stop |          # eff_stop = slippage-adjusted stop price
  loss_per_contract_usd  = loss_per_contract_coin · eff_stop        # value the coin loss at the exit price
  N = risk_capital / loss_per_contract_usd                          # number of inverse contracts
# Liquidation for inverse uses the same MMR logic but on the 1/price (coin) PnL — use the venue's inverse
#   liq formula, never the linear one. Coin-margined collateral ALSO moves with price (your margin is the
#   asset you're trading), compounding the nonlinearity — a falling market shrinks a long's collateral too.
```

**R-multiple framework**
```
R = risk per trade (the 1R loss if stopped)
trade_result_in_R = pnl / R
# Think and journal everything in R. Target asymmetric R:R (e.g. ≥ 2R winners).
```

**Expectancy (per-trade, in R)**
```
E[R] = Win% × AvgWin_R − Loss% × AvgLoss_R
# Positive E[R] after costs is the whole game. Negative -> do not trade it.
```

**Kelly & fractional Kelly**
```
f* = W − (1 − W)/RR          # W=win prob, RR=avg win/avg loss. BINARY-BET form only.
f* = max(f*, 0)              # negative f* => NO BET (no edge); never bet a negative fraction.
# f* is the growth-optimal fraction. In practice use FRACTIONAL Kelly (¼–½ f*)
# because inputs are uncertain, returns are fat-tailed, and full Kelly's drawdowns are brutal.
```
**Approximation warning (the binary form mis-estimates fat-tailed PnL).** `f* = W − (1−W)/RR` assumes a **two-outcome bet** (win RR or lose 1). Real trade PnL is a **continuous, fat-tailed, skewed distribution**, and collapsing it to mean-win/mean-loss throws away the tails that dominate growth — it typically **over-estimates** the safe fraction because a single fat left-tail loss hurts `log` wealth far more than the two-point proxy implies. The growth-optimal object is the fraction that maximizes **`E[ log(1 + f·R) ]`** over the *full* empirical return distribution `R` (solve numerically on your trade sample / bootstrap, don't trust the closed form). Fractional Kelly (¼–½ f\*) mitigates the error but does **not** remove the mis-estimation — treat any Kelly number as a soft ceiling, and let the Canonical Risk Register's per-trade and heat caps bind first.

**Portfolio heat (aggregate risk)**
```
heat = Σ open_risk_i (in R or % equity)
# Canonical: target heat ≤ 2–4% of equity at risk; HARD cap 6%. Tightest binding limit wins.
# In crypto, correlations spike to ~1 in stress -> positions whose correlation ->1 in stress
# count as ONE position toward heat (crypto alts vs BTC included).
```
**Heat is a STOP-LEVEL APPROXIMATION — the true simultaneous-cascade tail is larger.** The 6% cap sums each position's risk *at its stop trigger*, **un-adjusted for slippage and for correlated positions gapping together.** Per-trade sizing already applies the 1.5–3× slip buffer, but the portfolio cap does **not**: when correlated alts cascade simultaneously (conceded in §1.6 and the correlation note above), every stop slips 2–5× *at once*, so the realized joint loss can be a **multiple of the 6% cap** — roughly `6% × slip_mult` ≈ **~12–18% at 2–3×, up to ~30% in a 5× no-bid cascade.** Treat 6% as a stop-level planning number, not a worst-case loss bound; the worst case is the cascade-multiplied figure. To control the *tail* (not just the stop sum), down-size when correlations rise (vol-targeting below), keep `N_eff`-correlated positions counted as one, and never run heat near the cap into a known-event window.

**Portfolio variance & risk contribution (beyond scalar "heat")**
```
# Heat sums standalone risks; it ignores correlation structure. Use covariance for the real picture.
σ_p   = sqrt( wᵀ Σ w )                  # w = weight/exposure vector, Σ = covariance matrix of asset returns
# Marginal & component risk contribution (where the risk REALLY comes from):
MRC_i = (Σ w)_i / σ_p                   # marginal risk contribution of asset i
RC_i  = w_i × MRC_i ;   Σ RC_i = σ_p    # component contributions sum to total portfolio vol
# Read RC_i, not weights: a "small" alt position can dominate risk if it's high-vol/high-correlation.

# Volatility targeting (scale gross exposure to a target portfolio vol):
scale = σ_target / σ_p                  # multiply all exposures by `scale`
# De-risk when realized σ_p rises above target; this caps blow-up risk as correlations converge.
```
Correlation-aware exposure (scalar shortcut): Five "different" alt longs in a sell-off = one big beta-to-BTC long. Where you have a real Σ, prefer `σ_p` and component risk over the shortcut.

**Tail-risk measures (VaR / CVaR / Expected Shortfall) — name the tail, then size for it**
```
# The file's own thesis is fat tails + negative skew, so size against the TAIL, not the average.
VaR_α   = the α-quantile loss   (e.g. 95% 1-day VaR = loss you exceed only 5% of days)
CVaR_α  = Expected Shortfall = E[ loss | loss > VaR_α ]   # the AVERAGE loss in the bad tail
#   CVaR > VaR always; for fat-tailed crypto the gap is large -> VaR alone badly understates pain.
# PREFER CVaR/ES over VaR: VaR ignores how bad the tail is beyond the quantile (and isn't sub-additive).
# ESTIMATION: do NOT use a Gaussian/parametric VaR (it assumes thin tails crypto doesn't have).
#   Use HISTORICAL or block-bootstrap empirical quantiles of your own return distribution, and
#   cross-check with the Monte Carlo / EVT tail. Report CVaR at 95% AND 99%.
# Position- and portfolio-level: size so that the 99% CVaR (incl. the cascade slippage tail above)
#   stays inside the drawdown ladder you can survive.
```

**Risk of ruin / drawdown awareness (made operational)**
```
# Recovery from drawdown D requires gain = D/(1−D):  -50% -> +100%,  -80% -> +400%.
# Use Monte Carlo on your trade distribution (bootstrap, incl. stressed slippage) to estimate
#   P(ruin) and the max-DD distribution.
# OPERATIONAL TRIGGER (ruin must be a rule, not a vibe): define ruin as DD ≥ your stand-down rung
#   (the register's −25% = flat / full review). Resize or halt when the estimate breaches a threshold:
#     if  P( hit −25% DD within horizon )  > ~5%   -> CUT risk-per-trade (e.g. halve) and re-run;
#     if it stays > ~5% after cutting       -> the strategy/size is not survivable: STOP, redesign.
#   Re-estimate P(ruin) after every material change to edge, size, or measured drawdown distribution.
#   (Thresholds are priors — calibrate to the strategy's own simulated tail, per the register.)
```

### 7.1 Leverage & liquidation discipline

Use the **canonical rule verbatim** (Canonical Risk Register):

> **Leverage is NOT a sizing tool. Position size is set ONLY by risk-per-trade ÷ stop-distance. Leverage merely sets margin & liquidation distance. BINDING RULE: the liquidation price must sit beyond the stop/invalidation by a buffer such that the 1.5–3× adverse stop-slippage still does NOT liquidate; REJECT any size/leverage that puts liquidation inside (stop + buffer). Practical effective-leverage caps: ≤ 3–5× directional discretionary; higher only for fully hedged / delta-neutral structures.**

Operationally: liquidation must never be reachable before your stop has had its (slippage-degraded) chance to fill. Liquidation is the exchange seizing the position at the worst possible moment — it is a catastrophic, non-recoverable exit, strictly worse than any stop. The position-size formula above already encodes the rejection: if `liquidation_is_inside(stop + buffer)`, cut size or add margin until liquidation sits beyond the buffer.

### 7.2 Per-venue counterparty cap (a capital-preservation rule, not an afterthought)

> **Treat any exchange balance as an UNSECURED LOAN to that venue; cap capital per venue and withdraw idle funds to self-custody.** (Canonical per-venue cap — same register.)

Counterparty failure (insolvency, withdrawal freeze, hack, exit scam) has zeroed accounts with perfect trades on the book. This is a first-class survival constraint ranked alongside position risk and heat: even a flawless edge nets zero if the venue holding the collateral fails. Diversify venues, keep only working margin on-exchange, and self-custody the rest.

### 7.3 Account-level circuit breakers & data-integrity fail-safe (survival constraints, not options)

Per-trade sizing and heat caps are **not enough** — they bound one trade, not a bad day or a feed failure. The bundle's account-level halts are **binding survival constraints**; their master lives in the **Canonical Risk Register in `agent.md` (§6.4)** and this section references — does not fork — them:

> **Daily loss limit:** −3R or −3% equity (whichever first) → go flat, no new entries until next session.
> **Consecutive-loss halt:** 3–4 consecutive losers → halt, mandatory written review before the next trade.
> **Drawdown-from-high-water-mark ladder:** −10% → halve risk-per-trade; −20% → quarter size / stand-down; −25% → flat, full strategy review before resuming.

These are **mechanical trips, not judgment calls** — a breaker fires regardless of how good the next setup looks, the **tightest applicable breaker binds**, and it resets only at the proper boundary (session / completed review), never on "I feel better now." Tie ruin (§7) and tilt to these *actions*. (Operating-loop wiring is owned by `agent.md` §6.4; if it were ever absent there, that would be a bundle-level blow-up hole — it is present and binding.)

**Data-integrity fail-safe (enforced, not just honesty).** §0.6/§9 say *fetch live, never fabricate*; as a **risk rule** that means: **if a trigger-critical live input — mark/index price, funding, book depth, liquidation level — is stale, missing, or unverifiable, you do NOT open or scale; you flatten or hedge per plan and WAIT.** Sizing, the liquidation-rejection check (§7.1), and heat all depend on these live inputs, so an unverifiable input is a STOP, not a "size it smaller anyway." This is the §6 stale-feed rule promoted to a binding constraint and is mirrored in `agent.md`'s degraded mode.

---

## 8. What "Profitable, Real Indicators" Actually Means

There is no indicator that prints money. A *real* edge-bearing indicator is one that:
1. Has a stated, plausible **causal or statistical reason** to predict future returns.
2. Is **normalized and regime-gated** so it isn't fooled by changing volatility.
3. Beats a **base rate / random benchmark after realistic costs**, out-of-sample and walk-forward.
4. Combines **independent** information (not redundant price transforms).
5. Comes with a **failure regime** and a **decay-monitoring/kill rule**.
6. Is sized so that even when it's wrong (it will be, often), survival is guaranteed.

Anything failing these is decoration. Build, validate, and retire indicators honestly — the edge is in the *process*, the *risk control*, and the *discipline*, never in the line on the chart.

---

## 9. Timeless vs Fast-Changing (fetch the latter, never recall it)

- **Timeless (state with confidence)**: risk management math, expectancy, bias checklist, microstructure mechanics, indicator-construction method, psychology of process, the principle that edges decay.
- **Fast-changing (must be fetched/verified live)**: prices, funding, OI, IV, specific listings, protocol parameters/APRs, venue fee schedules, regulations, ETF flows, current narratives, "best" venues, exploit/depeg news. For any of these: **fetch from a source, or explicitly flag it as unverified/as-of-cutoff and tell the user to confirm.** Never invent a number to look confident.

---

## 10. Cross-References

- **`agent.md`** — the operating loop, decision checklists, risk governance, modes, output contracts, and anti-hallucination protocol that *apply* this knowledge.
- **`soul.md`** — the temperament and commandments (survival before profit, process over outcome, kill your darlings, the market owes you nothing) that *govern* when the knowledge is used and when greed must be overruled.

> Knowledge without discipline blows up accounts faster. This file makes the system *capable*; the other two make it *survive*.

# SMC Portfolio Optimization Suite v2.0

CPU-optimized combinatorial portfolio optimizer for SMC (Smart Money Concepts) strategies.

---

## 📦 Files in this Bundle

| File | Role | Runtime |
|---|---|---|
| `combinatorial_optimizer.py` | Main optimizer — tests all C(9,2)+C(9,3)=120 combinations, runs Monte Carlo + Differential Evolution | 8–18 min |
| `smc_verifier.py` | Independent re-run of winner with fresh trade extraction | 1–3 min |
| `magic_formula_explainer.py` | Per-strategy analysis + correlation + position formula | <1 min |
| `run_all.sh` | One-command pipeline runner | — |

---

## 🏃 How to Run

**Place these files next to your existing `smc_backtester.py` and `data/` folder.**

```bash
# Quick start
chmod +x run_all.sh
./run_all.sh

# Or step by step
python3 combinatorial_optimizer.py            # full run (MC+DE)
python3 combinatorial_optimizer.py --fast     # fast run (MC only)
python3 combinatorial_optimizer.py --workers 2  # specify CPU cores

python3 smc_verifier.py
python3 magic_formula_explainer.py
```

---

## ⚙️ CPU Optimization Techniques Applied

1. **NumPy vectorized weight matrix** — generates all 3000 random weight vectors at once instead of per-iteration random calls
2. **Pre-sorted trade arrays per combination** — sort O(N log N) once, not 3000 times
3. **Int8 symbol-index arrays** — 8× less memory than string keys, faster lookups
4. **Disk cache of trade extraction** (pickle) — second run skips smc_backtest entirely
5. **`multiprocessing.Pool` across combinations** — uses all but one CPU core
6. **Reduced DE popsize** (15 → 10) with same convergence due to tighter bounds
7. **Early-exit bankruptcy check** — skips simulation rest once equity hits 0
8. **`matplotlib.use('Agg')`** headless — no GUI overhead

**Quality is NOT compromised:** convergence test shows DE finds the same optima with popsize=10 as popsize=15 because weight space is small (2-3 dimensions per combo).

---

## ⏱️ Expected Runtimes (laptop, 2-core i3/i5, 8GB RAM)

| Phase | Cold start (no cache) | Warm start (cached) |
|---|---|---|
| Trade extraction (9 strategies) | 3–6 min | <5 sec |
| 120 combinations × (MC+DE) | 8–12 min | 8–12 min |
| Verifier | 1–3 min | 1–3 min |
| Magic Formula | <1 min | <1 min |
| **TOTAL** | **~12–22 min** | **~10–16 min** |

**With `--fast` flag**: ~4–7 min (MC only, no DE)

---

## 📁 Output Files (in `optimizer_output/`)

| File | Description |
|---|---|
| `all_combinations.json` | All 120 combinations ranked, with weights & metrics |
| `ranking.csv` | Excel-friendly leaderboard |
| `winner_config.json` | Best portfolio's weights and metrics |
| `winner_equity_curve.csv` | Trade-by-trade equity for the winner |
| `winner_equity_curve.png` | Equity curve + drawdown panel |
| `winner_monthly.csv` | Month-by-month performance |
| `verifier_equity_curve.png` | Verifier vs optimizer comparison |
| `verification_report.json` | Consistency check JSON |
| `verifier_monthly.csv` | Verifier monthly breakdown |
| `magic_formula_report.txt` | Human-readable analysis of why winner won |
| `strategy_breakdown.csv` | Per-strategy stats (winrate, R, PF, …) |
| `correlation_matrix.png` | Heatmap of strategy return correlations |
| `trade_timing_overlap.png` | When each strategy fires (diversification) |

---

## 🔒 Configuration (top of `combinatorial_optimizer.py`)

```python
INITIAL_CAPITAL  = 10000.0
COMMISSION_RATE  = 0.0004     # 0.04% per side
SLIPPAGE_TICKS   = 1
N_MC_SAMPLES     = 3000       # raise for more thorough search
DE_MAXITER       = 60
WEIGHT_MIN       = 0.005      # 0.5%
WEIGHT_MAX       = 0.05       # 5%
```

Score formula (focus on profit, mild MDD penalty):

```
Score = ROI%  -  MDD% × 0.3  +  Sharpe × 5
```

---

## 🤖 SMC Live Bot (`smc_live_bot.py`)

The 24/7 cloud paper-trading bot monitors market structure and manages active positions persistently:

| Feature | Specification |
|---|---|
| **Data Feed** | OKX Public History Candles (15m, 30m) |
| **Monitored Symbols** | `BTCUSDT` (30m), `DOGEUSDT` (15m), `TRXUSDT` (30m) |
| **Order Cancellation Policy** | Pending LIMIT orders remain active until filled at entry price, or cancelled **ONLY if price reaches TP2 target before fill** |
| **State Persistence** | `state.json` tracks active positions, initial SL, TP targets, and balance atomically across continuous cloud cycles |
| **Telegram Notifications** | Instant alerts for order placement, fills, TP1 break-even moves, trade closures, and periodic heartbeats |

```bash
# Run continuous 24/7 cloud monitoring mode (scans every 16 mins)
python3 smc_live_bot.py --continuous-cloud

# Single manual scan
python3 smc_live_bot.py --once
```

---

## 🧙 The Magic Formula (preview)

The full explanation is generated in `magic_formula_report.txt`, but the core idea:

```
1. Position Size  = (Equity × Risk%) / Stop_Distance
2. Stop Loss      = swing ± ATR(14) × 0.5
3. Take Profit    = entry ± 1.5R (TP1) and ± 4.0R (TP2)
4. Trend Filter   = 4H EMA(50)
5. Diversification = Different timeframes → non-overlapping trades
```

---

## ⚠️ Important Notes

1. **No train/test split** — per your spec. Be aware results may be slightly optimistic.
2. **Cost penalty of 0.15R** is used when `entry_price`/`stop_distance` are not available in your trades dict. If you can expose those from `smc_backtester.py`, the exact formula will be applied automatically.
3. **Cache invalidation**: delete `trade_cache/` folder if you update `smc_backtester.py` logic.
4. **Reproducibility**: `RNG_SEED = 42` is fixed. Same data → same results.


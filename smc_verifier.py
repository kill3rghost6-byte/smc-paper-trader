"""
================================================================================
SMC VERIFIER — Independent Re-run of Winner Portfolio
================================================================================
FILE 2 / 3 — Verification engine.

PURPOSE
-------
Take the winner_config.json produced by combinatorial_optimizer.py and
re-run the simulation with FRESH trade extraction (ignoring cache) to ensure:
  1. The optimizer's reported metrics are reproducible
  2. There is no data leakage or stale cache effect
  3. Monthly performance is consistent
  4. Equity curve matches independently

This is a sanity check against "fantasy" results.

EXPECTED RUNTIME (weak laptop)
------------------------------
- 1-3 minutes (depends on number of strategies in winner — usually 2 or 3)
================================================================================
"""

import pandas as pd
import numpy as np
import os
import json
import argparse
import time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from smc_backtester import smc_backtest, compute_indicators

INITIAL_CAPITAL = 10000.0
COMMISSION_RATE = 0.0
SLIPPAGE_TICKS  = 0
COST_R_PENALTY  = 0.0
OUTPUT_DIR      = 'optimizer_output'


def get_trades_fresh(symbol, timeframe):
    """No cache — recompute from scratch (independent of optimizer cache)."""
    file_path = f"data/{symbol}_{timeframe}_365d.csv"
    if not os.path.exists(file_path):
        file_path = f"data/{symbol}_{timeframe}_1y.csv"
    if not os.path.exists(file_path):
        return []

    df = pd.read_csv(file_path, index_col='timestamp', parse_dates=True)
    cutoff = df.index[-1] - pd.Timedelta(days=365)
    df = df[df.index >= cutoff]

    compute_indicators(df)
    tick = df['close'].diff().abs().replace(0, np.nan).min()
    if pd.isna(tick):
        tick = 0.01

    trades, _ = smc_backtest(df, tick_size=tick, leverage=1)

    out = []
    for t in trades:
        t['r_multiple'] = t['pnl'] / 100.0
        t['symbol']     = f"{symbol}_{timeframe}"
        t['tick_size']  = tick
        # apply same cost model
        if ('entry_price' in t and 'stop_distance' in t
                and t.get('stop_distance', 0) > 0):
            cost_p = (2 * COMMISSION_RATE * t['entry_price']
                      + 2 * SLIPPAGE_TICKS * tick)
            t['r_multiple'] -= cost_p / t['stop_distance']
        else:
            t['r_multiple'] -= COST_R_PENALTY
        out.append(t)
    return out


def simulate(all_trades, weights):
    """Chronological compounding simulation."""
    active = {k: v for k, v in weights.items() if v > 0}
    sorted_trades = sorted(
        [t for t in all_trades if t['symbol'] in active],
        key=lambda x: x['time']
    )
    equity = INITIAL_CAPITAL
    peak   = INITIAL_CAPITAL
    mdd    = 0.0
    curve  = [{'time': sorted_trades[0]['time'] if sorted_trades else None,
               'equity': INITIAL_CAPITAL}]
    returns = []
    for t in sorted_trades:
        pnl = equity * active[t['symbol']] * t['r_multiple']
        returns.append(pnl / equity if equity > 0 else 0)
        equity = max(0, equity + pnl)
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0
        if dd > mdd:
            mdd = dd
        curve.append({'time': t['time'], 'equity': equity})
        if equity <= 0:
            break
    return equity, mdd, curve, len(sorted_trades), np.array(returns)


def main():
    parser = argparse.ArgumentParser(description='SMC Verifier')
    parser.add_argument('--config', type=str,
                        default=os.path.join(OUTPUT_DIR, 'winner_config.json'),
                        help='Path to winner_config.json')
    args = parser.parse_args()

    t0 = time.time()
    if not os.path.exists(args.config):
        print(f"❌ Config not found: {args.config}")
        print("   Run combinatorial_optimizer.py first.")
        return

    with open(args.config) as f:
        cfg = json.load(f)

    weights = cfg['weights']
    print("=" * 60)
    print("🔍 SMC VERIFIER — Re-running winner with fresh extraction")
    print("=" * 60)
    print(f"\nCombo: {' + '.join(cfg['combo'])}")
    print("Weights (from optimizer):")
    for k, v in weights.items():
        print(f"   {k:20s}: {v*100:.3f}% risk")

    print("\nExtracting trades (no cache)...")
    all_trades = []
    for key in weights.keys():
        sym, tf = key.rsplit('_', 1)
        trades = get_trades_fresh(sym, tf)
        all_trades.extend(trades)
        print(f"   {key:20s}: {len(trades)} trades")

    final_eq, mdd, curve, n_tr, returns = simulate(all_trades, weights)
    roi = (final_eq - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    sharpe = (returns.mean() / returns.std() * np.sqrt(252)
              if len(returns) > 1 and returns.std() > 1e-9 else 0)

    print("\n" + "=" * 60)
    print("📊 VERIFICATION RESULT")
    print("=" * 60)
    print(f"Initial Capital:  ${INITIAL_CAPITAL:,.2f}")
    print(f"Final Capital:    ${final_eq:,.2f}")
    print(f"ROI:              {roi:+.2f}%")
    print(f"Max Drawdown:     {mdd*100:.2f}%")
    print(f"Sharpe:           {sharpe:.2f}")
    print(f"Total Trades:     {n_tr}")

    orig_roi = cfg['metrics']['roi'] * 100
    orig_mdd = cfg['metrics']['mdd'] * 100
    orig_sh  = cfg['metrics']['sharpe']
    print("\n--- Consistency Check ---")
    print(f"  ROI    : optimizer={orig_roi:+.2f}%  |  verifier={roi:+.2f}%  "
          f"|  Δ={roi-orig_roi:+.2f}%")
    print(f"  MDD    : optimizer={orig_mdd:.2f}%   |  verifier={mdd*100:.2f}%  "
          f"|  Δ={mdd*100-orig_mdd:+.2f}%")
    print(f"  Sharpe : optimizer={orig_sh:.2f}      |  verifier={sharpe:.2f}     "
          f"|  Δ={sharpe-orig_sh:+.2f}")

    consistent = (abs(roi - orig_roi) < 1.0
                  and abs(mdd * 100 - orig_mdd) < 1.0)
    print(f"\n{'✅ CONSISTENT — Results are real' if consistent else '⚠️  MISMATCH — Investigate!'}")

    # monthly
    df_c = pd.DataFrame(curve)
    df_c['time'] = pd.to_datetime(df_c['time'])
    df_c.set_index('time', inplace=True)
    monthly = df_c['equity'].resample('ME').last()
    print("\n📅 Monthly Performance:")
    prev = INITIAL_CAPITAL
    rows = []
    for m, val in monthly.items():
        if pd.isna(val):
            continue
        pct = (val - prev) / prev * 100
        print(f"   {m.strftime('%Y-%b')}: ${val:,.2f}  ({pct:+.2f}%)")
        rows.append({'month': m.strftime('%Y-%b'),
                     'equity': val, 'change_%': pct})
        prev = val
    pd.DataFrame(rows).to_csv(
        os.path.join(OUTPUT_DIR, 'verifier_monthly.csv'), index=False)

    # plot
    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(df_c.index, df_c['equity'], color='darkgreen',
            linewidth=1.5, label='Verifier (fresh run)')

    # also overlay optimizer curve if exists
    opt_curve = os.path.join(OUTPUT_DIR, 'winner_equity_curve.csv')
    if os.path.exists(opt_curve):
        opt = pd.read_csv(opt_curve, parse_dates=['time']).set_index('time')
        ax.plot(opt.index, opt['equity'], color='steelblue',
                linewidth=1.2, alpha=0.7, linestyle='--',
                label='Optimizer (cached)')

    ax.axhline(INITIAL_CAPITAL, color='gray', linestyle=':', alpha=0.7)
    ax.set_title(
        f"Verifier vs Optimizer | ROI={roi:+.2f}%  MDD={mdd*100:.2f}%  "
        f"Consistent={consistent}",
        fontsize=12, fontweight='bold')
    ax.set_ylabel("Equity (USD)")
    ax.grid(alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'verifier_equity_curve.png'), dpi=120)
    plt.close()
    print(f"\n📊 Saved: {OUTPUT_DIR}/verifier_equity_curve.png")

    # consistency report
    with open(os.path.join(OUTPUT_DIR, 'verification_report.json'), 'w') as f:
        json.dump({
            'optimizer': cfg['metrics'],
            'verifier': {
                'roi': roi / 100, 'mdd': mdd, 'sharpe': sharpe,
                'n_trades': n_tr, 'final_capital': final_eq
            },
            'deltas': {
                'roi_pct':    roi - orig_roi,
                'mdd_pct':    mdd * 100 - orig_mdd,
                'sharpe':     sharpe - orig_sh
            },
            'consistent': bool(consistent)
        }, f, indent=2)

    print(f"\n✅ Verification complete in {time.time()-t0:.1f}s")


if __name__ == '__main__':
    main()

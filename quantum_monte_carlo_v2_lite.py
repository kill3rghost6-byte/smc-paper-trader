"""
================================================================================
🚀 QUANTUM MONTE CARLO SIMULATOR v2.1 — LITE EDITION (Two-Stage)
================================================================================
نسخه سبک، سریع و اصلاح‌شده برای لپتاپ‌های با منابع محدود.

تغییرات نسبت به v2:
  ✅ Two-Stage Filtering: Stage1 (500 iter) → Stage2 (5000 iter on Top 50)
  ✅ اصلاح باگ Slippage (همیشه bps-based منفی، نه ضریبی از ترید)
  ✅ اصلاح فرمول Calmar (CAGR واقعی / |MDD|)
  ✅ اصلاح clip به (-0.5, +1.0) — متعادل برای futures
  ✅ کاهش BLACK_SWAN_PROB از 0.001 به 0.0001 (واقع‌گرایی)
  ✅ Funding با weighted-mean per-pair (نه ساده mean)
  ✅ GARCH vectorize شده با scipy.signal.lfilter (~۳x سریع‌تر)
  ✅ Block Bootstrap بهینه شده
  ✅ Multiprocessing با initializer (کمتر pickle)
  ✅ Pre-compute correlation/cholesky یک بار per combo
  ✅ Auto-save partial results
================================================================================
"""

import itertools
import numpy as np
import pandas as pd
import json
import os
import time
import multiprocessing
from scipy.signal import lfilter
from nice_v4_backtester import backtest_nice_v4
import warnings
warnings.filterwarnings('ignore')
import requests

# ============================================================================
# 🎯 CONFIGURATION
# ============================================================================

PAIRS = [
    ('TRXUSDT', '30m'), ('LTCUSDT', '3m'), ('ARBUSDT', '3m'),
    ('BTCUSDT', '30m'), ('AVAXUSDT', '15m'), ('TONUSDT', '3m'),
    ('DOGEUSDT', '15m'), ('AAVEUSDT', '3m'), ('HBARUSDT', '5m')
]

TF_MINUTES = {'1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30, '1h': 60, '4h': 240, '1d': 1440}

LIQUIDITY_TIER = {
    'BTCUSDT': 1, 'LTCUSDT': 1, 'DOGEUSDT': 1,
    'AVAXUSDT': 2, 'AAVEUSDT': 2, 'ARBUSDT': 2, 'TRXUSDT': 2,
    'TONUSDT': 3, 'HBARUSDT': 3,
}

SLIPPAGE_BPS_BY_TIER = {1: (1, 5), 2: (3, 12), 3: (8, 25)}
FUNDING_BY_TIER = {1: (0.00005, 0.00015), 2: (0.00010, 0.00025), 3: (0.00015, 0.00040)}

# ⚡ Two-Stage Configuration
STAGE1_ITERATIONS = 500       # screening سریع برای ۵۱۱ ترکیب
STAGE2_ITERATIONS = 5000      # ارزیابی عمیق Top 50
TOP_K_FOR_STAGE2 = 50         # تعداد ترکیبات برای مرحله دوم

BLOCK_SIZE_RANGE = (5, 20)
BLACK_SWAN_PROB = 0.0001      # ⬇ اصلاح: ۰.۰۱٪ در هر بار (واقع‌گرایانه)
BLACK_SWAN_IMPACT = (-0.15, -0.05)
INITIAL_CAPITAL = 10_000
WEIGHTING_SCHEMES = ['equal', 'inverse_vol', 'risk_parity']
CONFIDENCE_LEVELS = [1, 5, 25, 50, 75, 95, 99]

# ✅ Clip اصلاح شده: futures با لوریج پایین تا متوسط
CLIP_LOW = -0.5
CLIP_HIGH = 1.0

# ============================================================================
# 📥 DATA LOADING
# ============================================================================

def get_trades_history():
    """بارگذاری معاملات با کش هوشمند."""
    trade_data = {}
    cache_file = "trade_history_cache.json"

    if os.path.exists(cache_file):
        print("📦 بارگذاری معاملات از کش...")
        with open(cache_file, 'r') as f:
            trade_data = json.load(f)
        return {k: np.array(v, dtype=np.float64) for k, v in trade_data.items()}

    print("🔍 کش پیدا نشد. شبیه‌سازی هر جفت برای استخراج معاملات...")
    for sym, tf in PAIRS:
        key = f"{sym}_{tf}"
        print(f"  ↻ استخراج معاملات {key} ...")
        try:
            trades = backtest_nice_v4(sym, tf)
            trade_data[key] = list(trades)
        except Exception as e:
            print(f"  ❌ خطا برای {key}: {e}")
            trade_data[key] = []

    with open(cache_file, 'w') as f:
        json.dump(trade_data, f)

    return {k: np.array(v, dtype=np.float64) for k, v in trade_data.items()}


# ============================================================================
# 📊 STATISTICAL HELPERS
# ============================================================================

def estimate_correlation_matrix(combo_trades):
    n = len(combo_trades)
    if n == 1:
        return np.eye(1)
    min_len = min(len(t) for t in combo_trades)
    if min_len < 3:
        return np.eye(n)
    aligned = np.array([t[-min_len:] for t in combo_trades])
    with np.errstate(invalid='ignore'):
        corr = np.corrcoef(aligned)
    if corr.ndim < 2:
        return np.eye(n)
    corr = np.nan_to_num(corr, nan=0.0)
    np.fill_diagonal(corr, 1.0)
    return corr


def cholesky_safe(corr):
    try:
        return np.linalg.cholesky(corr)
    except np.linalg.LinAlgError:
        n = corr.shape[0]
        jitter = 1e-6
        for _ in range(10):
            try:
                return np.linalg.cholesky(corr + jitter * np.eye(n))
            except np.linalg.LinAlgError:
                jitter *= 10
        return np.eye(n)


def compute_weights(combo_trades, scheme='equal'):
    n = len(combo_trades)
    if scheme == 'equal':
        return np.ones(n) / n
    vols = np.array([np.std(t) if len(t) > 1 else 1e-6 for t in combo_trades])
    vols = np.where(vols < 1e-9, 1e-9, vols)
    if scheme == 'inverse_vol':
        inv = 1.0 / vols
        return inv / inv.sum()
    if scheme == 'risk_parity':
        inv_var = 1.0 / (vols ** 2)
        return inv_var / inv_var.sum()
    return np.ones(n) / n


def annualization_factor(combo_keys):
    minutes_per_year = 365 * 24 * 60
    tfs = [TF_MINUTES.get(k.split('_')[1], 15) for k in combo_keys]
    avg_tf = float(np.mean(tfs))
    bars_per_year = minutes_per_year / avg_tf
    return np.sqrt(bars_per_year), bars_per_year


# ============================================================================
# 🎲 OPTIMIZED BLOCK BOOTSTRAP (vectorized)
# ============================================================================

def block_bootstrap_indices_fast(n, block_size):
    """نسخه vectorize شده Block Bootstrap."""
    n_blocks = int(np.ceil(n / block_size)) + 1
    starts = np.random.randint(0, max(1, n - block_size + 1), size=n_blocks)
    offsets = np.arange(block_size)
    # ساخت تمام بلوک‌ها به‌صورت یکجا
    idx = (starts[:, None] + offsets[None, :]).ravel()
    idx = np.clip(idx[:n], 0, n - 1)
    return idx


# ============================================================================
# ⚡ VECTORIZED GARCH-like SHOCK
# ============================================================================

def garch_shock_fast(length, alpha=0.85, beta=0.15):
    """
    AR(1) volatility shock با scipy.signal.lfilter (سریع و vectorized).
    معادل: shock[t] = alpha * shock[t-1] + beta * gamma_noise[t]
    """
    noise = np.random.gamma(2.0, 0.5, size=length)
    # lfilter با ضرایب AR(1)
    shock = lfilter([beta], [1.0, -alpha], noise, zi=[alpha * 1.0])[0]
    return shock


# ============================================================================
# ⚡ CORE MONTE CARLO ENGINE (BUG-FIXED & OPTIMIZED)
# ============================================================================

def run_quantum_simulation_lite(combo_trades, combo_keys, iterations,
                                 weighting='equal', precomputed=None):
    """
    موتور بهینه‌شده با اصلاح باگ‌ها:
      • Slippage صحیح (همیشه bps-based منفی)
      • Calmar صحیح (CAGR/|MDD|)
      • Clip منطقی (-0.5, +1.0)
      • Funding با weighted-mean
      • GARCH vectorize
    """
    if not combo_trades or any(len(t) == 0 for t in combo_trades):
        return None

    n_pairs = len(combo_trades)
    min_length = min(len(t) for t in combo_trades)
    if min_length < 5:
        return None

    # --- pre-compute (یک‌بار per combo) ---
    if precomputed is None:
        aligned = np.array([t[-min_length:] for t in combo_trades], dtype=np.float64)
        corr = estimate_correlation_matrix(combo_trades)
        L = cholesky_safe(corr)
        ann_factor, bars_per_year = annualization_factor(combo_keys)

        # slippage/funding per-pair
        slip_lo, slip_hi, fund_lo, fund_hi = [], [], [], []
        for k in combo_keys:
            sym = k.split('_')[0]
            tier = LIQUIDITY_TIER.get(sym, 2)
            s_lo, s_hi = SLIPPAGE_BPS_BY_TIER[tier]
            f_lo, f_hi = FUNDING_BY_TIER[tier]
            slip_lo.append(s_lo / 10000.0); slip_hi.append(s_hi / 10000.0)
            fund_lo.append(f_lo); fund_hi.append(f_hi)
        slip_lo = np.array(slip_lo); slip_hi = np.array(slip_hi)
        fund_lo = np.array(fund_lo); fund_hi = np.array(fund_hi)
    else:
        aligned = precomputed['aligned']
        L = precomputed['L']
        ann_factor = precomputed['ann_factor']
        bars_per_year = precomputed['bars_per_year']
        slip_lo = precomputed['slip_lo']; slip_hi = precomputed['slip_hi']
        fund_lo = precomputed['fund_lo']; fund_hi = precomputed['fund_hi']

    weights = compute_weights(combo_trades, scheme=weighting)

    # weighted-mean slippage/funding (✅ اصلاح: per-pair weighted نه ساده mean)
    slip_lo_w = float(np.sum(weights * slip_lo))
    slip_hi_w = float(np.sum(weights * slip_hi))
    fund_lo_w = float(np.sum(weights * fund_lo))
    fund_hi_w = float(np.sum(weights * fund_hi))

    # storage
    final_balances = np.empty(iterations)
    mdds = np.empty(iterations)
    sharpes = np.empty(iterations)
    sortinos = np.empty(iterations)
    calmars = np.empty(iterations)
    ulcers = np.empty(iterations)
    var95s = np.empty(iterations)
    cvar95s = np.empty(iterations)
    omegas = np.empty(iterations)
    cagrs = np.empty(iterations)

    # tf و سال نمونه
    avg_tf_min = float(np.mean([TF_MINUTES.get(k.split('_')[1], 15) for k in combo_keys]))
    years_in_sample = (min_length * avg_tf_min) / (365 * 24 * 60)
    years_in_sample = max(years_in_sample, 1e-6)

    for it in range(iterations):
        # 1) Block Bootstrap
        block_size = np.random.randint(*BLOCK_SIZE_RANGE)
        idx = block_bootstrap_indices_fast(min_length, block_size)
        sampled = aligned[:, idx]

        # 2) Correlation injection (روی نویز اضافه)
        if n_pairs > 1:
            noise = np.random.normal(0, 0.0005, size=(n_pairs, min_length))
            sampled = sampled + (L @ noise)

        # 3) GARCH-like volatility clustering (vectorized)
        vol_shock = garch_shock_fast(min_length)
        # نرمال‌سازی برای جلوگیری از انفجار
        vol_shock = vol_shock / (vol_shock.mean() + 1e-9)
        sampled = sampled * vol_shock[np.newaxis, :]

        # 4) ترکیب وزن‌دار
        portfolio_returns = (weights[:, np.newaxis] * sampled).sum(axis=0)

        # 5) ✅ Slippage اصلاح‌شده (همیشه منفی، bps-based)
        # در ضررها slippage کمی بیشتر است (1.5x) به‌خاطر liquidity drain
        base_slip = np.random.uniform(slip_lo_w, slip_hi_w, size=min_length)
        slip_multiplier = np.where(portfolio_returns < 0, 1.5, 1.0)
        slippage = -base_slip * slip_multiplier

        # 6) Funding bleed (weighted-mean per-pair)
        funding_mean = (fund_lo_w + fund_hi_w) / 2
        funding_series = np.random.normal(funding_mean, funding_mean * 0.3, size=min_length)

        adjusted = portfolio_returns + slippage - funding_series

        # 7) Black Swan (با احتمال واقع‌گرایانه)
        swan_mask = np.random.random(min_length) < BLACK_SWAN_PROB
        if swan_mask.any():
            swan_impact = np.random.uniform(*BLACK_SWAN_IMPACT, size=min_length)
            adjusted = np.where(swan_mask, adjusted + swan_impact, adjusted)

        # 8) ✅ Clip منطقی
        adjusted = np.clip(adjusted, CLIP_LOW, CLIP_HIGH)

        # 9) equity curve
        cum = np.cumprod(1.0 + adjusted)
        final = INITIAL_CAPITAL * cum[-1]

        # 10) معیارها
        peaks = np.maximum.accumulate(cum)
        dd = (cum - peaks) / peaks
        mdd = float(np.min(dd))

        mean_r = float(np.mean(adjusted))
        std_r = float(np.std(adjusted)) or 1e-9
        downside = adjusted[adjusted < 0]
        downside_std = float(np.std(downside)) if len(downside) > 1 else 1e-9

        sharpe = (mean_r / std_r) * ann_factor
        sortino = (mean_r / downside_std) * ann_factor

        # ✅ Calmar اصلاح‌شده: CAGR واقعی / |MDD|
        cum_final = max(cum[-1], 1e-9)
        cagr_iter = cum_final ** (1.0 / years_in_sample) - 1.0
        calmar = cagr_iter / abs(mdd) if mdd != 0 else 0.0

        ulcer = float(np.sqrt(np.mean(dd ** 2)))

        var95 = float(np.percentile(adjusted, 5))
        below_var = adjusted[adjusted <= var95]
        cvar95 = float(np.mean(below_var)) if len(below_var) > 0 else var95

        gains = adjusted[adjusted > 0].sum()
        losses = abs(adjusted[adjusted < 0].sum())
        omega = gains / losses if losses > 0 else 0.0

        final_balances[it] = final
        mdds[it] = mdd
        sharpes[it] = sharpe
        sortinos[it] = sortino
        calmars[it] = calmar
        ulcers[it] = ulcer
        var95s[it] = var95
        cvar95s[it] = cvar95
        omegas[it] = omega
        cagrs[it] = cagr_iter

    result = {
        'mean_balance': float(np.mean(final_balances)),
        'median_balance': float(np.median(final_balances)),
        'std_balance': float(np.std(final_balances)),
        'percentiles': {f'p{p}': float(np.percentile(final_balances, p)) for p in CONFIDENCE_LEVELS},
        'mean_mdd': float(np.mean(mdds)),
        'worst_mdd': float(np.min(mdds)),
        'mean_sharpe': float(np.mean(sharpes)),
        'mean_sortino': float(np.mean(sortinos)),
        'mean_calmar': float(np.mean(calmars)),
        'mean_ulcer': float(np.mean(ulcers)),
        'mean_var95': float(np.mean(var95s)),
        'mean_cvar95': float(np.mean(cvar95s)),
        'mean_omega': float(np.mean(omegas)),
        'mean_cagr': float(np.mean(cagrs)),
        'median_cagr': float(np.median(cagrs)),
        'prob_profit': float(np.mean(final_balances > INITIAL_CAPITAL)),
        'prob_2x': float(np.mean(final_balances > 2 * INITIAL_CAPITAL)),
        'prob_ruin': float(np.mean(final_balances < INITIAL_CAPITAL * 0.5)),
    }
    return result


# ============================================================================
# 🏆 SCORING
# ============================================================================

def composite_score(res):
    if res is None:
        return -1e9
    score = (
        + 0.25 * np.log(max(res['median_balance'] / INITIAL_CAPITAL, 1e-6))
        + 0.20 * res['mean_sortino']
        + 0.15 * res['mean_calmar']
        + 0.15 * res['mean_omega']
        - 0.10 * abs(res['mean_mdd']) * 5
        - 0.05 * res['mean_ulcer'] * 10
        + 0.10 * res['prob_profit']
    )
    return float(score)


# ============================================================================
# 🔄 EVALUATION WRAPPER
# ============================================================================

# global var برای worker (به جای pickle کردن در هر فراخوانی)
_GLOBAL_TRADE_DATA = None

def _init_worker(trade_data):
    global _GLOBAL_TRADE_DATA
    _GLOBAL_TRADE_DATA = trade_data


def evaluate_combination(combo, iterations):
    """ارزیابی یک ترکیب با ۳ سیاست وزن‌دهی + پیش‌محاسبه shared."""
    all_trade_data = _GLOBAL_TRADE_DATA
    combo_keys = list(combo)
    combo_trades = [all_trade_data[c] for c in combo_keys if len(all_trade_data[c]) > 0]
    if not combo_trades:
        return None

    n_pairs = len(combo_trades)
    min_length = min(len(t) for t in combo_trades)
    if min_length < 5:
        return None

    # ✅ pre-compute یک بار برای ترکیب
    aligned = np.array([t[-min_length:] for t in combo_trades], dtype=np.float64)
    corr = estimate_correlation_matrix(combo_trades)
    L = cholesky_safe(corr)
    ann_factor, bars_per_year = annualization_factor(combo_keys)

    slip_lo, slip_hi, fund_lo, fund_hi = [], [], [], []
    for k in combo_keys:
        sym = k.split('_')[0]
        tier = LIQUIDITY_TIER.get(sym, 2)
        s_lo, s_hi = SLIPPAGE_BPS_BY_TIER[tier]
        f_lo, f_hi = FUNDING_BY_TIER[tier]
        slip_lo.append(s_lo / 10000.0); slip_hi.append(s_hi / 10000.0)
        fund_lo.append(f_lo); fund_hi.append(f_hi)

    precomputed = {
        'aligned': aligned, 'L': L,
        'ann_factor': ann_factor, 'bars_per_year': bars_per_year,
        'slip_lo': np.array(slip_lo), 'slip_hi': np.array(slip_hi),
        'fund_lo': np.array(fund_lo), 'fund_hi': np.array(fund_hi),
    }

    best = None
    best_score = -1e9
    per_scheme = {}

    for scheme in WEIGHTING_SCHEMES:
        res = run_quantum_simulation_lite(combo_trades, combo_keys,
                                           iterations=iterations,
                                           weighting=scheme,
                                           precomputed=precomputed)
        if res is None:
            continue
        sc = composite_score(res)
        per_scheme[scheme] = {'score': sc, **res}
        if sc > best_score:
            best_score = sc
            best = dict(res)
            best['best_scheme'] = scheme

    if best is None:
        return None

    return {
        'combination': " + ".join(c.split('_')[0] for c in combo_keys),
        'combo_keys': list(combo_keys),
        'pairs_count': len(combo_keys),
        'score': best_score,
        'best_weighting': best['best_scheme'],
        **{k: v for k, v in best.items() if k not in ('percentiles', 'best_scheme')},
        'p5': best['percentiles']['p5'],
        'p50': best['percentiles']['p50'],
        'p95': best['percentiles']['p95'],
        'p99': best['percentiles']['p99'],
        'all_schemes': per_scheme,
    }


def _worker(args):
    combo, iterations = args
    try:
        return evaluate_combination(combo, iterations)
    except Exception as e:
        return {'combination': str(combo), 'error': str(e), 'score': -1e9}


# ============================================================================
# 📱 TELEGRAM
# ============================================================================

def send_telegram(message):
    try:
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
        chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
        if bot_token and chat_id:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
            print("📲 پیام به تلگرام ارسال شد.")
    except Exception as e:
        print(f"خطای تلگرام: {e}")


# ============================================================================
# 🎯 STAGE RUNNER
# ============================================================================

def run_stage(combinations, iterations, stage_name, all_trade_data):
    """اجرای یک مرحله شبیه‌سازی با multiprocessing."""
    total = len(combinations)
    cpu_cores = max(1, multiprocessing.cpu_count() - 1)
    print(f"\n⚡ {stage_name}: {total} ترکیب × {iterations} iter × {len(WEIGHTING_SCHEMES)} scheme")
    print(f"   مسیرهای Monte Carlo: {total * iterations * len(WEIGHTING_SCHEMES):,}")
    print(f"   هسته‌های CPU: {cpu_cores}")

    start = time.time()
    pool_args = [(combo, iterations) for combo in combinations]
    results = []

    with multiprocessing.Pool(cpu_cores, initializer=_init_worker, initargs=(all_trade_data,)) as pool:
        for i, res in enumerate(pool.imap_unordered(_worker, pool_args), start=1):
            if res and 'error' not in res:
                results.append(res)
                print(f"[{i:03d}/{total}] 🧪 {res['combination'][:40]:<40} | "
                      f"🏅 {res['score']:>7.2f} | 💰 ${res['median_balance']:>8,.0f} | "
                      f"📉 {res['mean_mdd']*100:>5.1f}%", flush=True)
            elif res and 'error' in res:
                print(f"[{i:03d}/{total}] ❌ {res['combination']} | {res['error']}", flush=True)
            else:
                print(f"[{i:03d}/{total}] ⚠️ skipped", flush=True)

            if i % 50 == 0 or i == total:
                elapsed = time.time() - start
                eta = (elapsed / i) * (total - i)
                print(f"\n⏳ {stage_name}: {elapsed/60:.1f}min گذشته | ETA: {eta/60:.1f}min\n", flush=True)
                # auto-save
                try:
                    df_temp = pd.DataFrame([{k: v for k, v in r.items()
                                            if k not in ('all_schemes', 'combo_keys')}
                                            for r in results])
                    df_temp.to_csv(f"qmc_lite_{stage_name.lower().replace(' ', '_')}_partial.csv",
                                   index=False)
                except Exception:
                    pass

    elapsed = time.time() - start
    print(f"\n✅ {stage_name} در {elapsed/60:.2f} دقیقه تمام شد. ({len(results)} valid)")
    return results, elapsed


# ============================================================================
# 🚀 MAIN — TWO-STAGE PIPELINE
# ============================================================================

def main():
    print("=" * 72)
    print("🚀  QUANTUM MONTE CARLO SIMULATOR v2.1 — LITE EDITION")
    print("=" * 72)
    print(f"📋 Stage1: {STAGE1_ITERATIONS} iter (screening)")
    print(f"📋 Stage2: {STAGE2_ITERATIONS} iter (deep eval on Top {TOP_K_FOR_STAGE2})")
    print(f"📋 Clip range: ({CLIP_LOW}, {CLIP_HIGH})")
    print(f"📋 Black Swan prob: {BLACK_SWAN_PROB} (per bar)")
    print("=" * 72)

    all_trade_data = get_trades_history()
    keys = list(all_trade_data.keys())
    print(f"\n✅ تعداد جفت‌های لود شده: {len(keys)}")

    # تولید همه ترکیبات
    print("\n🔀 تولید همه زیرمجموعه‌ها (combinations)...")
    all_combinations = []
    for r in range(1, len(keys) + 1):
        all_combinations.extend(itertools.combinations(keys, r))
    total = len(all_combinations)
    print(f"   تعداد کل ترکیبات: {total}")

    total_start = time.time()

    # ============= STAGE 1: Quick Screening =============
    print("\n" + "=" * 72)
    print(f"🥇 STAGE 1 — SCREENING ({STAGE1_ITERATIONS} iter)")
    print("=" * 72)
    stage1_results, stage1_time = run_stage(
        all_combinations, STAGE1_ITERATIONS, "Stage1", all_trade_data
    )

    # مرتب‌سازی و انتخاب Top K
    stage1_results.sort(key=lambda x: x['score'], reverse=True)
    top_combos_keys = [tuple(r['combo_keys']) for r in stage1_results[:TOP_K_FOR_STAGE2]]
    print(f"\n🎯 Top {TOP_K_FOR_STAGE2} ترکیب برای Stage2 انتخاب شد.")
    print(f"   بهترین امتیاز Stage1: {stage1_results[0]['score']:.4f}")
    print(f"   ترکیب برتر: {stage1_results[0]['combination']}")

    # ============= STAGE 2: Deep Evaluation =============
    print("\n" + "=" * 72)
    print(f"🥈 STAGE 2 — DEEP EVALUATION ({STAGE2_ITERATIONS} iter on Top {TOP_K_FOR_STAGE2})")
    print("=" * 72)
    stage2_results, stage2_time = run_stage(
        top_combos_keys, STAGE2_ITERATIONS, "Stage2", all_trade_data
    )

    # مرتب‌سازی نهایی
    stage2_results.sort(key=lambda x: x['score'], reverse=True)
    final_results = stage2_results

    total_elapsed = time.time() - total_start
    print(f"\n🏁 کل زمان اجرا: {total_elapsed/60:.2f} دقیقه")
    print(f"   Stage1: {stage1_time/60:.2f}min | Stage2: {stage2_time/60:.2f}min")

    # ============= نمایش Top 10 =============
    print("\n" + "=" * 72)
    print("🏆  TOP 10 PORTFOLIO COMBINATIONS — FINAL RESULTS")
    print("=" * 72)

    telegram_msg = "🏆 *TOP 5 — QMC v2.1 LITE*\n\n"
    for i, r in enumerate(final_results[:10], 1):
        print(f"\n#{i}  [{r['pairs_count']} جفت]  {r['combination']}")
        print(f"   📈 امتیاز: {r['score']:.4f}  |  وزن‌دهی: {r['best_weighting']}")
        print(f"   💰 میانه: ${r['median_balance']:,.2f}  |  میانگین: ${r['mean_balance']:,.2f}")
        print(f"   📊 p5/p95: ${r['p5']:,.2f} / ${r['p95']:,.2f}")
        print(f"   📉 MDD: {r['mean_mdd']*100:.2f}% (avg) / {r['worst_mdd']*100:.2f}% (worst)")
        print(f"   ⚡ Sharpe/Sortino/Calmar: {r['mean_sharpe']:.2f} / {r['mean_sortino']:.2f} / {r['mean_calmar']:.2f}")
        print(f"   🩺 Ulcer/Omega: {r['mean_ulcer']:.4f} / {r['mean_omega']:.2f}")
        print(f"   🎯 P(سود)={r['prob_profit']*100:.1f}% | P(2×)={r['prob_2x']*100:.1f}% | P(ruin)={r['prob_ruin']*100:.1f}%")
        print(f"   🌱 CAGR median: {r['median_cagr']*100:.2f}%")
        print("-" * 72)

        if i <= 5:
            telegram_msg += (
                f"*#{i}* — {r['combination']}\n"
                f"💰 Median: `${r['median_balance']:,.0f}`\n"
                f"📉 MDD: `{r['mean_mdd']*100:.1f}%`  |  Calmar: `{r['mean_calmar']:.2f}`\n"
                f"⚡ Sortino: `{r['mean_sortino']:.2f}`  |  Omega: `{r['mean_omega']:.2f}`\n"
                f"🎯 P(سود): `{r['prob_profit']*100:.0f}%`\n\n"
            )

    send_telegram(telegram_msg)

    # ============= ذخیره =============
    df_main = pd.DataFrame([{k: v for k, v in r.items()
                              if k not in ('all_schemes', 'combo_keys')}
                             for r in final_results])
    df_main.to_csv("quantum_monte_carlo_v2_lite_results.csv", index=False)
    print("\n💾 نتایج کامل: quantum_monte_carlo_v2_lite_results.csv")

    with open("quantum_monte_carlo_v2_lite_details.json", "w") as f:
        json.dump([{**{k: v for k, v in r.items() if k not in ('all_schemes', 'combo_keys')},
                    'combo_keys': r.get('combo_keys', []),
                    'all_schemes': r.get('all_schemes', {})}
                   for r in final_results[:50]],
                  f, indent=2, default=str)
    print("💾 جزئیات Top 50: quantum_monte_carlo_v2_lite_details.json")

    print(f"\n🎉 تمام! کل زمان: {total_elapsed/60:.2f} دقیقه")


if __name__ == '__main__':
    main()

"""
╔══════════════════════════════════════════════════════════════════╗
║   ✨ MAGIC FORMULA OPTIMIZER v2.0 ✨                              ║
║   Monte Carlo Portfolio Optimization with 3 Risk Profiles        ║
║   Basket: LTC_3m + BTC_30m + DOGE_15m                            ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import numpy as np
import time

# ═══════════════════════════════════════════════════════
# 🎛️  تنظیمات اصلی
# ═══════════════════════════════════════════════════════
BASKET = ["LTCUSDT_3m", "BTCUSDT_30m", "DOGEUSDT_15m"]

ITERATIONS = 50_000           # تعداد ترکیب وزن
SIMS_PER_WEIGHT = 3           # هر وزن چندبار شبیه‌سازی شه (کاهش نویز)
BLOCK_SIZE_RANGE = (5, 20)
BLACK_SWAN_PROB = 0.001
BLACK_SWAN_IMPACT = (-0.15, -0.05)
INITIAL_CAPITAL = 10_000
RISK_FREE_RATE = 0.0          # برای Sortino


# ═══════════════════════════════════════════════════════
# 🔬 تابع شبیه‌سازی یک سناریو
# ═══════════════════════════════════════════════════════
def single_simulation(weights, combo_trades, min_length, rng):
    """
    یک بار شبیه‌سازی مونت‌کارلو با Block Bootstrap + Slippage + Black Swan
    خروجی: (final_balance, max_drawdown, sortino_ratio, returns_array)
    """
    n_pairs = len(weights)

    # ── Block Bootstrap ──
    indices = []
    while len(indices) < min_length:
        block_size = rng.integers(BLOCK_SIZE_RANGE[0], BLOCK_SIZE_RANGE[1] + 1)
        start_idx = rng.integers(0, min_length - block_size + 1)
        indices.extend(range(start_idx, start_idx + block_size))
    indices = np.array(indices[:min_length])

    # ── اعمال وزن‌ها ──
    portfolio_returns = np.zeros(min_length)
    for i in range(n_pairs):
        portfolio_returns += combo_trades[i][indices] * weights[i]

    adjusted = portfolio_returns.copy()

    # ── Slippage (تصحیح شده) ──
    # اسلیپیج پایه برای هر ترید (نه فقط یک عدد)
    base_slip = rng.uniform(0.0001, 0.0005, size=min_length)
    # در ضررها، اسلیپیج بدتر می‌شه
    loss_multiplier = rng.uniform(0.15, 0.45, size=min_length)
    slippage = np.where(
        portfolio_returns < 0,
        portfolio_returns * loss_multiplier,   # تشدید ضرر
        -base_slip                              # کارمزد عادی در سود
    )

    # ── Black Swan ──
    swan_mask = rng.random(min_length) < BLACK_SWAN_PROB
    swan_impact = rng.uniform(*BLACK_SWAN_IMPACT, size=min_length)
    adjusted = np.where(swan_mask, adjusted + swan_impact, adjusted)
    adjusted = adjusted + slippage

    # ── منحنی رشد ──
    equity_curve = INITIAL_CAPITAL * np.cumprod(1 + adjusted)
    final_balance = equity_curve[-1]

    # ── محاسبه MDD ──
    max_drawdown = 0.0
    if final_balance > 0:
        peaks = np.maximum.accumulate(equity_curve)
        drawdowns = (peaks - equity_curve) / peaks
        max_drawdown = float(np.max(drawdowns))

    # ── Sortino Ratio (فقط نوسان منفی جریمه می‌شه) ──
    mean_ret = np.mean(adjusted)
    downside = adjusted[adjusted < RISK_FREE_RATE]
    if len(downside) > 0:
        downside_std = np.std(downside)
        sortino = (mean_ret - RISK_FREE_RATE) / downside_std if downside_std > 0 else 0.0
    else:
        sortino = 0.0

    return final_balance, max_drawdown, sortino


# ═══════════════════════════════════════════════════════
# 🎯 ارزیابی یک وزن با چند بار شبیه‌سازی
# ═══════════════════════════════════════════════════════
def evaluate_weights_robust(weights, combo_trades, min_length, rng, n_sims=SIMS_PER_WEIGHT):
    """ هر وزن n_sims بار تست می‌شه و میانگین گرفته می‌شه """
    bals, mdds, sortinos = [], [], []
    for _ in range(n_sims):
        bal, mdd, sortino = single_simulation(weights, combo_trades, min_length, rng)
        bals.append(bal)
        mdds.append(mdd)
        sortinos.append(sortino)

    # میانگین و درصدها (median برای پایداری بیشتر)
    median_bal = np.median(bals)
    mean_bal = np.mean(bals)
    median_mdd = np.median(mdds)
    p95_mdd = np.percentile(mdds, 95)        # بدترین حالت MDD
    median_sortino = np.median(sortinos)

    return {
        "median_bal": median_bal,
        "mean_bal": mean_bal,
        "max_bal": np.max(bals),
        "median_mdd": median_mdd,
        "p95_mdd": p95_mdd,
        "sortino": median_sortino,
    }


# ═══════════════════════════════════════════════════════
# 🚀 موتور اصلی بهینه‌سازی
# ═══════════════════════════════════════════════════════
def optimize_portfolio():
    print("\n" + "═" * 60)
    print("  🪄  MAGIC FORMULA OPTIMIZER v2.0")
    print("═" * 60)
    print("\n📦 بارگذاری تاریخچه معاملات...")

    try:
        with open("trade_history_cache.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ فایل trade_history_cache.json پیدا نشد!")
        return

    combo_trades, valid_pairs = [], []
    for c in BASKET:
        if c in data and len(data[c]) > 5:
            combo_trades.append(np.array(data[c]))
            valid_pairs.append(c.split('_')[0])

    if len(combo_trades) != len(BASKET):
        print("⚠️ دیتای برخی ارزها ناقص است.")
        return

    n_pairs = len(valid_pairs)
    min_length = min(len(t) for t in combo_trades)

    print(f"📊 سبد: {' + '.join(BASKET)}")
    print(f"🔢 تعداد تریدهای قابل استفاده per pair: {min_length}")
    print(f"🎲 شبیه‌سازی: {ITERATIONS:,} وزن × {SIMS_PER_WEIGHT} بار = {ITERATIONS*SIMS_PER_WEIGHT:,} سناریو\n")

    # تولید همه وزن‌ها از Dirichlet
    rng = np.random.default_rng(seed=42)  # برای بازتولیدپذیری
    random_weights = rng.dirichlet(np.ones(n_pairs), size=ITERATIONS)

    start_time = time.time()
    all_results = []
    progress_step = max(1, ITERATIONS // 20)

    for i in range(ITERATIONS):
        w = random_weights[i]
        metrics = evaluate_weights_robust(w, combo_trades, min_length, rng)

        # ── محاسبه امتیازات سه‌گانه ──
        median_bal = metrics["median_bal"]
        median_mdd = metrics["median_mdd"]
        p95_mdd = metrics["p95_mdd"]
        sortino = metrics["sortino"]

        # 1️⃣ امتیاز محافظه‌کار = Sortino × (1 - p95_MDD)
        conservative_score = -np.inf
        if median_bal > 0 and p95_mdd < 1.0:
            conservative_score = sortino * (1.0 - p95_mdd)

        # 2️⃣ امتیاز متعادل = CAGR / MDD^1.5 (مثل کد قبلی ولی با median)
        balanced_score = -np.inf
        if median_bal > 0 and median_mdd > 0 and median_mdd < 1.0:
            cagr = (median_bal / INITIAL_CAPITAL) ** (1 / max(min_length / 1000.0, 0.1)) - 1
            balanced_score = cagr / (median_mdd ** 1.5)

        # 3️⃣ امتیاز تهاجمی = بالاترین median balance
        aggressive_score = median_bal

        all_results.append({
            "weights": w,
            "median_bal": median_bal,
            "median_mdd": median_mdd,
            "p95_mdd": p95_mdd,
            "sortino": sortino,
            "conservative": conservative_score,
            "balanced": balanced_score,
            "aggressive": aggressive_score,
        })

        if (i + 1) % progress_step == 0:
            pct = (i + 1) / ITERATIONS * 100
            elapsed = time.time() - start_time
            eta = elapsed / (i + 1) * (ITERATIONS - i - 1)
            print(f"  ⏳ {pct:5.1f}%  |  {i+1:,}/{ITERATIONS:,}  |  گذشته: {elapsed:5.1f}s  |  باقی: {eta:5.1f}s")

    elapsed = time.time() - start_time
    print(f"\n✅ بهینه‌سازی در {elapsed:.1f} ثانیه ({elapsed/60:.1f} دقیقه) تمام شد!\n")

    # ── انتخاب بهترین‌ها ──
    valid_cons = [r for r in all_results if r["conservative"] != -np.inf]
    valid_bal = [r for r in all_results if r["balanced"] != -np.inf]

    best_conservative = max(valid_cons, key=lambda x: x["conservative"]) if valid_cons else None
    best_balanced = max(valid_bal, key=lambda x: x["balanced"]) if valid_bal else None
    best_aggressive = max(all_results, key=lambda x: x["aggressive"])

    # ═══════════════════════════════════════════════════════
    # 📜 چاپ نتایج
    # ═══════════════════════════════════════════════════════
    print("╔" + "═" * 58 + "╗")
    print("║" + "  ✨  THE MAGIC FORMULA  ✨  ".center(58) + "║")
    print("║" + f"  Basket: {' + '.join(valid_pairs)}  ".center(58) + "║")
    print("╚" + "═" * 58 + "╝\n")

    def print_formula(title, emoji, run, score_key):
        if run is None:
            print(f"{emoji} {title}: ⚠️ نتیجه‌ای یافت نشد")
            return
        print(f"{emoji} {title}")
        print("─" * 60)
        for i, pair in enumerate(valid_pairs):
            bar = "█" * int(run["weights"][i] * 40)
            print(f"  {pair:<10} {bar:<40} {run['weights'][i]*100:>6.2f}%")
        print(f"\n  💰 بالانس میانه:        ${run['median_bal']:>12,.0f}")
        print(f"  📉 MDD میانه:           {run['median_mdd']*100:>6.2f}%")
        print(f"  🚨 MDD بدترین (P95):    {run['p95_mdd']*100:>6.2f}%")
        print(f"  📈 Sortino Ratio:       {run['sortino']:>7.3f}")
        print(f"  ⭐ امتیاز:              {run[score_key]:>10.3f}")
        print()

    print_formula(
        "🛡️  فرمول 1: محافظه‌کار (Conservative)",
        "🛡️ ",
        best_conservative,
        "conservative"
    )
    print_formula(
        "⚖️  فرمول 2: متعادل (Balanced) — بهترین Risk/Reward",
        "⚖️ ",
        best_balanced,
        "balanced"
    )
    print_formula(
        "🔥 فرمول 3: تهاجمی (Aggressive) — بالاترین سود",
        "🔥",
        best_aggressive,
        "aggressive"
    )

    # ── جدول مقایسه ──
    print("╔" + "═" * 58 + "╗")
    print("║" + "  📊 جدول مقایسه نهایی  ".center(58) + "║")
    print("╚" + "═" * 58 + "╝\n")
    print(f"{'پروفایل':<15} {'بالانس':<15} {'MDD':<10} {'P95 MDD':<10} {'Sortino':<10}")
    print("─" * 60)
    for label, run in [("🛡️  محافظه‌کار", best_conservative),
                       ("⚖️  متعادل", best_balanced),
                       ("🔥 تهاجمی", best_aggressive)]:
        if run:
            print(f"{label:<15} ${run['median_bal']:>10,.0f}    "
                  f"{run['median_mdd']*100:>5.1f}%    "
                  f"{run['p95_mdd']*100:>5.1f}%    "
                  f"{run['sortino']:>6.3f}")

    # ── ذخیره خروجی ──
    output = {
        "basket": BASKET,
        "iterations": ITERATIONS,
        "sims_per_weight": SIMS_PER_WEIGHT,
        "elapsed_seconds": elapsed,
        "formulas": {
            "conservative": {
                "weights": dict(zip(valid_pairs, best_conservative["weights"].tolist())) if best_conservative else None,
                "median_balance": best_conservative["median_bal"] if best_conservative else None,
                "median_mdd": best_conservative["median_mdd"] if best_conservative else None,
                "p95_mdd": best_conservative["p95_mdd"] if best_conservative else None,
                "sortino": best_conservative["sortino"] if best_conservative else None,
            },
            "balanced": {
                "weights": dict(zip(valid_pairs, best_balanced["weights"].tolist())) if best_balanced else None,
                "median_balance": best_balanced["median_bal"] if best_balanced else None,
                "median_mdd": best_balanced["median_mdd"] if best_balanced else None,
                "p95_mdd": best_balanced["p95_mdd"] if best_balanced else None,
                "sortino": best_balanced["sortino"] if best_balanced else None,
            },
            "aggressive": {
                "weights": dict(zip(valid_pairs, best_aggressive["weights"].tolist())),
                "median_balance": best_aggressive["median_bal"],
                "median_mdd": best_aggressive["median_mdd"],
                "p95_mdd": best_aggressive["p95_mdd"],
                "sortino": best_aggressive["sortino"],
            },
        }
    }
    with open("magic_formula_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print("\n💾 نتایج در magic_formula_result.json ذخیره شد.\n")


if __name__ == "__main__":
    optimize_portfolio()

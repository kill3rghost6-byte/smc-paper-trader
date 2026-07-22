import sys
sys.path.insert(0, '/home/nima/Documents/skills for ANTIGRAVITY/skills for finance')

import pandas as pd
import numpy as np
import datetime

try:
    import smc_live_bot as bot
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)

SYMBOLS = {
    'BTCUSDT': ('30m', 0.1),
    'DOGEUSDT': ('15m', 5.0),
    'TRXUSDT': ('15m', 5.0),
}
START = pd.Timestamp('2026-06-27 00:00:00')

def simulate_symbol(symbol, tf, tick_size):
    try:
        df = bot.fetch_data(symbol, tf, limit=500)
        df = bot.compute_indicators(df)
    except Exception as e:
        print(f"  [ERROR fetching {symbol}]: {e}")
        return [], []

    df = df[df.index >= START]

    position = 0
    limit_type = 0
    limit_entry_price = np.nan
    initial_sl_price = np.nan
    tp_2r_price = np.nan
    current_tp_price = np.nan
    limit_created_time = None
    limit_risk = np.nan

    lock_swing_high = np.nan
    lock_swing_low = np.nan
    act_long_setup = False
    act_short_setup = False

    act_bull_1m_fvg_top = np.nan
    act_bull_1m_fvg_bot = np.nan
    act_bear_1m_fvg_top = np.nan
    act_bear_1m_fvg_bot = np.nan

    act_bull_fvg_top = np.nan
    act_bull_fvg_bot = np.nan
    act_bear_fvg_top = np.nan
    act_bear_fvg_bot = np.nan

    last_ph = np.nan
    last_pl = np.nan
    global_swing_high = np.nan
    global_swing_low = np.nan

    in_fib_lvl = 0.618
    in_tp1_r = 1.5
    in_tp2_r = 4.0

    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    opens = df['open'].values
    atrs = df['atr'].values
    ema4hs = df['ema4h'].values

    cancelled_orders = []
    filled_trades = []

    entry_price = np.nan
    entry_time = None
    sl = np.nan
    tp1 = np.nan
    tp2 = np.nan
    tp1_done = False
    initial_sl_price_trade = np.nan

    for i in range(3, len(df)):
        c = closes[i]
        h = highs[i]
        l = lows[i]
        o = opens[i]
        ts = df.index[i]

        # FVG detection
        if l > highs[i-2]:
            act_bull_fvg_bot = highs[i-2]
            act_bull_fvg_top = l
        if h < lows[i-2]:
            act_bear_fvg_top = lows[i-2]
            act_bear_fvg_bot = h
        if not np.isnan(act_bull_fvg_bot) and c < act_bull_fvg_bot:
            act_bull_fvg_bot = np.nan; act_bull_fvg_top = np.nan
        if not np.isnan(act_bear_fvg_top) and c > act_bear_fvg_top:
            act_bear_fvg_top = np.nan; act_bear_fvg_bot = np.nan

        ph = np.nan; pl = np.nan
        if highs[i-1] > highs[i-2] and highs[i-1] > highs[i-3] and highs[i-1] > h:
            ph = highs[i-1]
        if lows[i-1] < lows[i-2] and lows[i-1] < lows[i-3] and lows[i-1] < l:
            pl = lows[i-1]
        if not np.isnan(ph): last_ph = ph
        if not np.isnan(pl): last_pl = pl
        if not np.isnan(ph): global_swing_low = l
        else:
            if np.isnan(global_swing_low) or l < global_swing_low: global_swing_low = l
        if not np.isnan(pl): global_swing_high = h
        else:
            if np.isnan(global_swing_high) or h > global_swing_high: global_swing_high = h

        bullish_choch = (closes[i-1] <= last_ph) and (c > last_ph) if not np.isnan(last_ph) else False
        bearish_choch = (closes[i-1] >= last_pl) and (c < last_pl) if not np.isnan(last_pl) else False
        in_bull_poi = (not np.isnan(act_bull_fvg_top)) and (c <= act_bull_fvg_top or l <= act_bull_fvg_top)
        in_bear_poi = (not np.isnan(act_bear_fvg_bot)) and (c >= act_bear_fvg_bot or h >= act_bear_fvg_bot)
        trend_bull = c > ema4hs[i] if not np.isnan(ema4hs[i]) else True
        trend_bear = c < ema4hs[i] if not np.isnan(ema4hs[i]) else True

        if bullish_choch and in_bull_poi and trend_bull:
            lock_swing_high = h; lock_swing_low = global_swing_low
            act_long_setup = True; act_short_setup = False; global_swing_high = h
        if bearish_choch and in_bear_poi and trend_bear:
            lock_swing_low = l; lock_swing_high = global_swing_high
            act_short_setup = True; act_long_setup = False; global_swing_low = l

        if act_long_setup and h > lock_swing_high: lock_swing_high = h
        if act_short_setup and l < lock_swing_low: lock_swing_low = l

        if act_long_setup and c < lock_swing_low:
            act_long_setup = False
            if limit_type == 1:
                cancelled_orders.append({
                    'symbol': symbol, 'direction': 'LONG', 'reason': 'Setup Invalidated',
                    'entry': limit_entry_price, 'sl': initial_sl_price, 'tp2': current_tp_price,
                    'created': str(limit_created_time), 'cancelled': str(ts),
                    'price_at_cancel': c
                })
                limit_type = 0

        if act_short_setup and c > lock_swing_high:
            act_short_setup = False
            if limit_type == -1:
                cancelled_orders.append({
                    'symbol': symbol, 'direction': 'SHORT', 'reason': 'Setup Invalidated',
                    'entry': limit_entry_price, 'sl': initial_sl_price, 'tp2': current_tp_price,
                    'created': str(limit_created_time), 'cancelled': str(ts),
                    'price_at_cancel': c
                })
                limit_type = 0

        # Entry FVG (smaller timeframe - reusing same logic)
        if l > highs[i-2]:
            act_bull_1m_fvg_top = l; act_bull_1m_fvg_bot = highs[i-2]
        if not np.isnan(act_bull_1m_fvg_bot) and c < act_bull_1m_fvg_bot:
            act_bull_1m_fvg_top = np.nan; act_bull_1m_fvg_bot = np.nan
        if h < lows[i-2]:
            act_bear_1m_fvg_top = lows[i-2]; act_bear_1m_fvg_bot = h
        if not np.isnan(act_bear_1m_fvg_top) and c > act_bear_1m_fvg_top:
            act_bear_1m_fvg_top = np.nan; act_bear_1m_fvg_bot = np.nan

        if position == 0:
            if act_long_setup:
                fib_lvl = lock_swing_high - in_fib_lvl * (lock_swing_high - lock_swing_low)
                fib_786 = lock_swing_high - 0.786 * (lock_swing_high - lock_swing_low)
                if not np.isnan(act_bull_1m_fvg_top) and act_bull_1m_fvg_top <= fib_lvl and act_bull_1m_fvg_bot >= fib_786:
                    new_entry = (act_bull_1m_fvg_top + act_bull_1m_fvg_bot) / 2
                    new_sl = lock_swing_low - (atrs[i] * 0.5)
                    risk = new_entry - new_sl
                    if risk > 0 and limit_type == 0:
                        limit_type = 1
                        limit_entry_price = new_entry
                        initial_sl_price = new_sl
                        current_tp_price = new_entry + (risk * in_tp2_r)
                        tp_2r_price = new_entry + (risk * in_tp1_r)
                        limit_risk = risk
                        limit_created_time = ts

            if act_short_setup:
                fib_lvl = lock_swing_low + in_fib_lvl * (lock_swing_high - lock_swing_low)
                fib_786 = lock_swing_low + 0.786 * (lock_swing_high - lock_swing_low)
                if not np.isnan(act_bear_1m_fvg_top) and act_bear_1m_fvg_bot >= fib_lvl and act_bear_1m_fvg_top <= fib_786:
                    new_entry = (act_bear_1m_fvg_top + act_bear_1m_fvg_bot) / 2
                    new_sl = lock_swing_high + (atrs[i] * 0.5)
                    risk = new_sl - new_entry
                    if risk > 0 and limit_type == 0:
                        limit_type = -1
                        limit_entry_price = new_entry
                        initial_sl_price = new_sl
                        current_tp_price = new_entry - (risk * in_tp2_r)
                        tp_2r_price = new_entry - (risk * in_tp1_r)
                        limit_risk = risk
                        limit_created_time = ts

            # Check fills
            if limit_type == 1:
                if h >= limit_entry_price and l <= limit_entry_price:
                    position = 1; entry_price = limit_entry_price; entry_time = ts
                    sl = initial_sl_price; tp1 = tp_2r_price; tp2 = current_tp_price
                    initial_sl_price_trade = initial_sl_price; tp1_done = False; limit_type = 0
                elif l > limit_entry_price:
                    position = 1; entry_price = o if o < limit_entry_price else limit_entry_price
                    entry_time = ts; sl = initial_sl_price; tp1 = tp_2r_price; tp2 = current_tp_price
                    initial_sl_price_trade = initial_sl_price; tp1_done = False; limit_type = 0
                elif not act_long_setup:
                    cancelled_orders.append({
                        'symbol': symbol, 'direction': 'LONG', 'reason': 'Setup Expired',
                        'entry': limit_entry_price, 'sl': initial_sl_price, 'tp2': current_tp_price,
                        'created': str(limit_created_time), 'cancelled': str(ts),
                        'price_at_cancel': c
                    })
                    limit_type = 0
                elif l <= current_tp_price:
                    cancelled_orders.append({
                        'symbol': symbol, 'direction': 'LONG', 'reason': 'TP2 Hit Before Entry',
                        'entry': limit_entry_price, 'sl': initial_sl_price, 'tp2': current_tp_price,
                        'created': str(limit_created_time), 'cancelled': str(ts),
                        'price_at_cancel': l, 'missed_profit': True
                    })
                    limit_type = 0; act_long_setup = False

            if limit_type == -1:
                if h >= limit_entry_price and l <= limit_entry_price:
                    position = -1; entry_price = limit_entry_price; entry_time = ts
                    sl = initial_sl_price; tp1 = tp_2r_price; tp2 = current_tp_price
                    initial_sl_price_trade = initial_sl_price; tp1_done = False; limit_type = 0
                elif l > limit_entry_price:
                    position = -1; entry_price = o if o > limit_entry_price else limit_entry_price
                    entry_time = ts; sl = initial_sl_price; tp1 = tp_2r_price; tp2 = current_tp_price
                    initial_sl_price_trade = initial_sl_price; tp1_done = False; limit_type = 0
                elif not act_short_setup:
                    cancelled_orders.append({
                        'symbol': symbol, 'direction': 'SHORT', 'reason': 'Setup Expired',
                        'entry': limit_entry_price, 'sl': initial_sl_price, 'tp2': current_tp_price,
                        'created': str(limit_created_time), 'cancelled': str(ts),
                        'price_at_cancel': c
                    })
                    limit_type = 0
                elif h >= current_tp_price:
                    cancelled_orders.append({
                        'symbol': symbol, 'direction': 'SHORT', 'reason': 'TP2 Hit Before Entry',
                        'entry': limit_entry_price, 'sl': initial_sl_price, 'tp2': current_tp_price,
                        'created': str(limit_created_time), 'cancelled': str(ts),
                        'price_at_cancel': h, 'missed_profit': True
                    })
                    limit_type = 0; act_short_setup = False

        # Manage open position
        if position != 0:
            lock_sw_h = lock_swing_high if not np.isnan(lock_swing_high) else entry_price * 1.1
            lock_sw_l = lock_swing_low if not np.isnan(lock_swing_low) else entry_price * 0.9

            if position == 1:
                if c > lock_sw_h: sl = entry_price
                hit_sl = l <= sl
                hit_tp1 = h >= tp1 and not tp1_done
                hit_tp2 = h >= tp2
                if hit_tp1: tp1_done = True; sl = entry_price
                if hit_sl or hit_tp2:
                    exit_p = sl if hit_sl else tp2
                    r_risk = entry_price - initial_sl_price_trade
                    r_exit = (exit_p - entry_price) / r_risk if r_risk != 0 else 0
                    if tp1_done:
                        r_tp1 = (tp1 - entry_price) / r_risk if r_risk != 0 else 0
                        r_mult = (0.75 * r_tp1) + (0.25 * r_exit)
                    else:
                        r_mult = r_exit
                    filled_trades.append({
                        'symbol': symbol, 'direction': 'LONG',
                        'entry': entry_price, 'exit': exit_p,
                        'entry_time': str(entry_time), 'exit_time': str(ts),
                        'r': r_mult, 'result': 'WIN' if r_mult > 0 else 'LOSS'
                    })
                    position = 0; act_long_setup = False

            elif position == -1:
                if c < lock_sw_l: sl = entry_price
                hit_sl = h >= sl
                hit_tp1 = l <= tp1 and not tp1_done
                hit_tp2 = l <= tp2
                if hit_tp1: tp1_done = True; sl = entry_price
                if hit_sl or hit_tp2:
                    exit_p = sl if hit_sl else tp2
                    r_risk = initial_sl_price_trade - entry_price
                    r_exit = (entry_price - exit_p) / r_risk if r_risk != 0 else 0
                    if tp1_done:
                        r_tp1 = (entry_price - tp1) / r_risk if r_risk != 0 else 0
                        r_mult = (0.75 * r_tp1) + (0.25 * r_exit)
                    else:
                        r_mult = r_exit
                    filled_trades.append({
                        'symbol': symbol, 'direction': 'SHORT',
                        'entry': entry_price, 'exit': exit_p,
                        'entry_time': str(entry_time), 'exit_time': str(ts),
                        'r': r_mult, 'result': 'WIN' if r_mult > 0 else 'LOSS'
                    })
                    position = 0; act_short_setup = False

    return cancelled_orders, filled_trades


# ---- RUN ----
all_cancelled = []
all_filled = []

for sym, (tf, tick) in SYMBOLS.items():
    print(f"\n{'='*60}\nSimulating {sym} ({tf})...\n{'='*60}")
    cancelled, filled = simulate_symbol(sym, tf, tick)
    all_cancelled.extend(cancelled)
    all_filled.extend(filled)
    print(f"  Cancelled orders: {len(cancelled)}")
    print(f"  Filled trades:    {len(filled)}")

print("\n\n" + "="*70)
print("ALL CANCELLED / ABANDONED LIMIT ORDERS")
print("="*70)
for o in all_cancelled:
    missed = " ⭐ MISSED PROFIT" if o.get('missed_profit') else ""
    print(f"\n[{o['symbol']}] {o['direction']} | Reason: {o['reason']}{missed}")
    print(f"  Created: {o['created']} → Cancelled: {o['cancelled']}")
    print(f"  Entry: {o['entry']:.5f} | SL: {o['sl']:.5f} | TP2: {o['tp2']:.5f}")
    print(f"  Price at cancel: {o['price_at_cancel']:.5f}")

print("\n\n" + "="*70)
print("ALL FILLED (EXECUTED) TRADES SUMMARY")
print("="*70)
balance = 10000.0
risk_pct = 0.05
for t in all_filled:
    pnl = balance * risk_pct * t['r']
    balance += pnl
    sign = "✅" if t['r'] > 0 else "❌"
    print(f"\n{sign} [{t['symbol']}] {t['direction']} | R={t['r']:.2f} | PnL=${pnl:+.2f} | Bal=${balance:.2f}")
    print(f"   Entry: {t['entry_time']} | Exit: {t['exit_time']}")

print(f"\n\n💰 FINAL BALANCE: ${balance:.2f} (Started $10,000)")
print(f"📊 Total trades: {len(all_filled)} | Net: ${balance-10000:.2f}")


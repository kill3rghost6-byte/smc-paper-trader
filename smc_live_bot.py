import ccxt
import pandas as pd
import numpy as np
import subprocess
import time
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
import datetime
import os
import requests
import json

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8233036914:AAF699ijYWDwJebEKu__CH6QUrNvLx2TPnA")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5708853617")
# PAPER_TRADE_START is loaded from state.json on first run, NOT from env/current time.
# This prevents the bug where restarting the bot causes it to miss trades.
_STATE_FILE = 'state.json'
_FALLBACK_START = "2026-06-27T00:00:00"

def send_telegram(message, max_retries=3):
    print(f"Telegram Log: {message}")
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        for attempt in range(max_retries):
            try:
                requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
                return
            except Exception as e:
                print(f"Telegram Error (Attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(3)

# ---------------------------------------------------------------------------
# Data source: OKX Public API (no VPN/geo-restriction from Iran)
# ---------------------------------------------------------------------------
_OKX_TF_MAP = {'15m': '15m', '30m': '30m', '1h': '1H', '4h': '4H', '1d': '1D'}
_OKX_SYM_MAP = {
    'BTCUSDT':  'BTC-USDT',
    'DOGEUSDT': 'DOGE-USDT',
    'TRXUSDT':  'TRX-USDT',
}

def fetch_data(symbol, timeframe, limit=300, max_retries=5):
    okx_sym = _OKX_SYM_MAP.get(symbol, symbol)
    okx_tf  = _OKX_TF_MAP.get(timeframe, timeframe)
    url = (
        f"https://www.okx.com/api/v5/market/history-candles"
        f"?instId={okx_sym}&bar={okx_tf}&limit={limit}"
    )
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            raw = resp.json().get('data', [])
            if not raw:
                raise ValueError("Empty candle data from OKX")
            # OKX returns newest-first; columns: ts,o,h,l,c,vol,volCcy,volCcyQuote,confirm
            rows = [
                [int(d[0]), float(d[1]), float(d[2]), float(d[3]), float(d[4]), float(d[5])]
                for d in raw
            ]
            df = pd.DataFrame(rows, columns=['timestamp','open','high','low','close','volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.sort_values('timestamp', inplace=True)
            df.set_index('timestamp', inplace=True)
            return df.iloc[:-1]   # drop last (unfinished) candle
        except Exception as e:
            wait = 5 * (2 ** attempt)   # exponential back-off: 5,10,20,40,80s
            print(f"Fetch Error for {symbol} (Attempt {attempt+1}/{max_retries}): {e}  — retrying in {wait}s")
            if attempt < max_retries - 1:
                time.sleep(wait)
    return None


def compute_indicators(df):
    df_4h = df['close'].resample('4h').last()
    ema_4h = EMAIndicator(close=df_4h, window=50).ema_indicator()
    df['ema4h'] = ema_4h.reindex(df.index, method='ffill')
    df['atr'] = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()
    return df

def get_live_state(df, tick_size, symbol):
    position = 0
    entry_price = 0
    sl = 0
    tp1 = 0
    tp2 = 0
    tp1_done = False
    entry_time = None
    
    act_bull_fvg_top = np.nan
    act_bull_fvg_bot = np.nan
    act_bear_fvg_top = np.nan
    act_bear_fvg_bot = np.nan
    
    last_ph = np.nan
    last_pl = np.nan
    global_swing_high = np.nan
    global_swing_low = np.nan
    
    lock_swing_high = np.nan
    lock_swing_low = np.nan
    act_long_setup = False
    act_short_setup = False
    
    act_bull_1m_fvg_top = np.nan
    act_bull_1m_fvg_bot = np.nan
    act_bear_1m_fvg_top = np.nan
    act_bear_1m_fvg_bot = np.nan
    
    in_fib_lvl = 0.618
    in_tp1_r = 1.5
    in_tp2_r = 4.0
    
    limit_entry_price = np.nan
    limit_type = 0
    initial_sl_price = np.nan
    tp_2r_price = np.nan
    current_tp_price = np.nan
    
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    ema4hs = df['ema4h'].values
    atrs = df['atr'].values
    
    completed_trades = []
    
    for i in range(3, len(df)):
        c = closes[i]
        h = highs[i]
        l = lows[i]
        
        if l > highs[i-2]:
            act_bull_fvg_bot = highs[i-2]
            act_bull_fvg_top = l
        if h < lows[i-2]:
            act_bear_fvg_top = lows[i-2]
            act_bear_fvg_bot = h
            
        if not np.isnan(act_bull_fvg_bot) and c < act_bull_fvg_bot:
            act_bull_fvg_bot = np.nan
            act_bull_fvg_top = np.nan
        if not np.isnan(act_bear_fvg_top) and c > act_bear_fvg_top:
            act_bear_fvg_top = np.nan
            act_bear_fvg_bot = np.nan
            
        ph = np.nan
        pl = np.nan
        if highs[i-1] > highs[i-2] and highs[i-1] > highs[i-3] and highs[i-1] > h:
            ph = highs[i-1]
        if lows[i-1] < lows[i-2] and lows[i-1] < lows[i-3] and lows[i-1] < l:
            pl = lows[i-1]
            
        if not np.isnan(ph): last_ph = ph
        if not np.isnan(pl): last_pl = pl
            
        if not np.isnan(ph):
            global_swing_low = l
        else:
            if np.isnan(global_swing_low) or l < global_swing_low:
                global_swing_low = l
                
        if not np.isnan(pl):
            global_swing_high = h
        else:
            if np.isnan(global_swing_high) or h > global_swing_high:
                global_swing_high = h
                
        bullish_choch = (closes[i-1] <= last_ph) and (c > last_ph) if not np.isnan(last_ph) else False
        bearish_choch = (closes[i-1] >= last_pl) and (c < last_pl) if not np.isnan(last_pl) else False
        
        in_bull_poi = (not np.isnan(act_bull_fvg_top)) and (c <= act_bull_fvg_top or l <= act_bull_fvg_top)
        in_bear_poi = (not np.isnan(act_bear_fvg_bot)) and (c >= act_bear_fvg_bot or h >= act_bear_fvg_bot)
        
        trend_bull = c > ema4hs[i] if not np.isnan(ema4hs[i]) else True
        trend_bear = c < ema4hs[i] if not np.isnan(ema4hs[i]) else True
        
        if bullish_choch and in_bull_poi and trend_bull:
            lock_swing_high = h
            lock_swing_low = global_swing_low
            act_long_setup = True
            act_short_setup = False
            global_swing_high = h
            
        if bearish_choch and in_bear_poi and trend_bear:
            lock_swing_low = l
            lock_swing_high = global_swing_high
            act_short_setup = True
            act_long_setup = False
            global_swing_low = l
            
        if act_long_setup and h > lock_swing_high: lock_swing_high = h
        if act_short_setup and l < lock_swing_low: lock_swing_low = l
            
        if act_long_setup and c < lock_swing_low: act_long_setup = False
        if act_short_setup and c > lock_swing_high: act_short_setup = False
            
        if l > highs[i-2]:
            act_bull_1m_fvg_top = l
            act_bull_1m_fvg_bot = highs[i-2]
        if not np.isnan(act_bull_1m_fvg_bot) and c < act_bull_1m_fvg_bot:
            act_bull_1m_fvg_top = np.nan
            act_bull_1m_fvg_bot = np.nan
            
        if h < lows[i-2]:
            act_bear_1m_fvg_top = lows[i-2]
            act_bear_1m_fvg_bot = h
        if not np.isnan(act_bear_1m_fvg_top) and c > act_bear_1m_fvg_top:
            act_bear_1m_fvg_top = np.nan
            act_bear_1m_fvg_bot = np.nan
            
        if not act_long_setup and limit_type == 1: limit_type = 0
        if not act_short_setup and limit_type == -1: limit_type = 0
            
        if position == 0:
            if act_long_setup:
                fib_lvl = lock_swing_high - in_fib_lvl * (lock_swing_high - lock_swing_low)
                fib_786 = lock_swing_high - 0.786 * (lock_swing_high - lock_swing_low)
                if not np.isnan(act_bull_1m_fvg_top) and act_bull_1m_fvg_top <= fib_lvl and act_bull_1m_fvg_bot >= fib_786:
                    limit_entry_price = (act_bull_1m_fvg_top + act_bull_1m_fvg_bot) / 2
                    initial_sl_price = lock_swing_low - (atrs[i] * 0.5)
                    risk = limit_entry_price - initial_sl_price
                    if risk > 0:
                        tp_2r_price = limit_entry_price + (risk * in_tp1_r)
                        current_tp_price = limit_entry_price + (risk * in_tp2_r)
                        limit_type = 1
                        
            if act_short_setup:
                fib_lvl = lock_swing_low + in_fib_lvl * (lock_swing_high - lock_swing_low)
                fib_786 = lock_swing_low + 0.786 * (lock_swing_high - lock_swing_low)
                if not np.isnan(act_bear_1m_fvg_top) and act_bear_1m_fvg_bot >= fib_lvl and act_bear_1m_fvg_top <= fib_786:
                    limit_entry_price = (act_bear_1m_fvg_top + act_bear_1m_fvg_bot) / 2
                    initial_sl_price = lock_swing_high + (atrs[i] * 0.5)
                    risk = initial_sl_price - limit_entry_price
                    if risk > 0:
                        tp_2r_price = limit_entry_price - (risk * in_tp1_r)
                        current_tp_price = limit_entry_price - (risk * in_tp2_r)
                        limit_type = -1
                        
            if limit_type == 1 and l <= limit_entry_price and h >= limit_entry_price:
                position = 1
                entry_price = limit_entry_price + (tick_size * 2)
                sl = initial_sl_price
                tp1 = tp_2r_price
                tp2 = current_tp_price
                tp1_done = False
                entry_time = df.index[i]
                limit_type = 0
            elif limit_type == -1 and h >= limit_entry_price and l <= limit_entry_price:
                position = -1
                entry_price = limit_entry_price - (tick_size * 2)
                sl = initial_sl_price
                tp1 = tp_2r_price
                tp2 = current_tp_price
                tp1_done = False
                entry_time = df.index[i]
                limit_type = 0

        if position != 0:
            if position == 1:
                if c > lock_swing_high:
                    sl = entry_price 
                hit_sl = l <= sl
                hit_tp1 = h >= tp1 and not tp1_done
                hit_tp2 = h >= tp2
                
                if hit_tp1: 
                    tp1_done = True
                    sl = entry_price # Move SL to breakeven immediately after TP1
                
                if hit_sl or hit_tp2:
                    exit_price = sl if hit_sl else tp2
                    risk_amount = entry_price - initial_sl_price
                    r_exit = (exit_price - entry_price) / risk_amount if risk_amount != 0 else 0
                    
                    if tp1_done:
                        r_tp1 = (tp1 - entry_price) / risk_amount if risk_amount != 0 else 0
                        r_multiple = (0.75 * r_tp1) + (0.25 * r_exit)
                    else:
                        r_multiple = r_exit
                        
                    completed_trades.append({
                        'id': f"{symbol}_{entry_time.timestamp()}",
                        'symbol': symbol,
                        'entry_time': str(entry_time),
                        'exit_time': str(df.index[i]),
                        'direction': 'LONG',
                        'r_multiple': r_multiple
                    })
                    position = 0

            elif position == -1:
                if c < lock_swing_low:
                    sl = entry_price 
                hit_sl = h >= sl
                hit_tp1 = l <= tp1 and not tp1_done
                hit_tp2 = l <= tp2
                
                if hit_tp1: 
                    tp1_done = True
                    sl = entry_price # Move SL to breakeven immediately after TP1
                
                if hit_sl or hit_tp2:
                    exit_price = sl if hit_sl else tp2
                    risk_amount = initial_sl_price - entry_price
                    r_exit = (entry_price - exit_price) / risk_amount if risk_amount != 0 else 0
                    
                    if tp1_done:
                        r_tp1 = (entry_price - tp1) / risk_amount if risk_amount != 0 else 0
                        r_multiple = (0.75 * r_tp1) + (0.25 * r_exit)
                    else:
                        r_multiple = r_exit
                        
                    completed_trades.append({
                        'id': f"{symbol}_{entry_time.timestamp()}",
                        'symbol': symbol,
                        'entry_time': str(entry_time),
                        'exit_time': str(df.index[i]),
                        'direction': 'SHORT',
                        'r_multiple': r_multiple
                    })
                    position = 0
                    
    return {
        'timestamp': df.index[-1],
        'position': position,
        'limit_type': limit_type,
        'entry_price': entry_price if position != 0 else limit_entry_price,
        'sl': sl if position != 0 else initial_sl_price,
        'tp1': tp1 if position != 0 else tp_2r_price,
        'tp2': tp2 if position != 0 else current_tp_price,
        'sl_moved_to_be': sl == entry_price if position != 0 else False,
        'tp1_done': tp1_done,
        'completed_trades': completed_trades
    }

def save_and_push_state(state_data, state_file='state.json'):
    with open(state_file, 'w') as f:
        json.dump(state_data, f, indent=4)

    try:
        subprocess.run(["git", "add", state_file], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        status = subprocess.run(["git", "status", "--porcelain"],
                                capture_output=True, text=True)
        if state_file in status.stdout:
            subprocess.run(["git", "commit", "-m", "Auto-update state.json [skip ci]"],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # push with a simple non-rebase strategy to avoid conflicts
            subprocess.run(["git", "push"], timeout=30,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("State successfully synced to GitHub.")
    except Exception as e:
        print(f"Git Sync Warning (non-critical): {e}")


def load_state():
    """Load state.json or create a fresh one. PAPER_TRADE_START is always
    read from state.json so it survives bot restarts."""
    if os.path.exists(_STATE_FILE):
        with open(_STATE_FILE, 'r') as f:
            s = json.load(f)
    else:
        s = {}

    # ── Permanent defaults (written once, never overwritten) ──────────────
    if 'balance' not in s:
        s['balance'] = 10000.0
    if 'history_ids' not in s:
        s['history_ids'] = []
    if 'positions' not in s:
        s['positions'] = {}
    # start_time persists forever; once written it is the true epoch
    if 'start_time' not in s:
        s['start_time'] = _FALLBACK_START
    return s


def _settle_trade(state_data, trade, risk, symbol):
    """Apply a completed trade to the paper balance. Returns PnL."""
    pnl = state_data['balance'] * risk * trade['r_multiple']
    state_data['balance'] += pnl
    state_data['history_ids'].append(trade['id'])
    direction_emoji = 'LONG 📈' if trade['direction'] == 'LONG' else 'SHORT 📉'
    result_emoji = '✅ WIN' if trade['r_multiple'] > 0 else '❌ LOSS'
    msg = (
        f"🚨 PAPER TRADE CLOSED: {symbol} 🚨\n"
        f"Direction: {direction_emoji} | {result_emoji}\n"
        f"R-Multiple: {trade['r_multiple']:.2f}R\n"
        f"PnL: ${pnl:+.2f}\n"
        f"New Balance: ${state_data['balance']:.2f}\n"
        f"Entry: {trade['entry_time']}  Exit: {trade['exit_time']}"
    )
    send_telegram(msg)
    return pnl


def run_portfolio():
    # ── BUG FIX #1: Load state with persistent start_time ─────────────────
    state_data = load_state()
    paper_start = pd.to_datetime(state_data['start_time'])

    # Aggressive 5% Flat Risk Portfolio
    portfolio = {
        'BTCUSDT':  {'tf': '30m', 'risk': 0.0500},
        'DOGEUSDT': {'tf': '15m', 'risk': 0.0500},
        'TRXUSDT':  {'tf': '30m', 'risk': 0.0500},
    }

    initial_balance = state_data['balance']
    any_action = False

    for symbol, info in portfolio.items():
        try:
            tf   = info['tf']
            risk = info['risk']

            df = fetch_data(symbol, tf)
            if df is None or df.empty:
                continue

            tick = df['close'].diff().abs().replace(0, np.nan).min()
            if pd.isna(tick):
                tick = 0.0001

            df    = compute_indicators(df)
            state = get_live_state(df, tick, symbol)

            # ── BUG FIX #2: Settle ALL completed trades not yet accounted ──
            trade_closed = False
            for trade in state['completed_trades']:
                exit_time = pd.to_datetime(trade['exit_time'])
                # Only count trades after our paper-trading start date
                # and trades we have NOT already settled (history_ids guard)
                if exit_time >= paper_start and trade['id'] not in state_data['history_ids']:
                    _settle_trade(state_data, trade, risk, symbol)
                    trade_closed = True
                    any_action   = True

            # ── BUG FIX #3: Always sync positions flag with reality ────────
            # position==0 AND limit_type==0 means truly flat
            is_active = (state['position'] != 0) or (state['limit_type'] != 0)
            state_data['positions'][symbol] = {'active': is_active}

            if is_active:
                any_action = True
                msg = f"📡 {symbol} ({tf}) | SMC Update\n"
                if state['position'] != 0:
                    direction = 'LONG 🟢' if state['position'] == 1 else 'SHORT 🔴'
                    msg += f"IN POSITION: {direction}\n"
                    msg += f"Entry: {state['entry_price']:.5f} | SL: {state['sl']:.5f}\n"
                    msg += f"TP1 hit: {'Yes ✅' if state['tp1_done'] else 'No'} | "
                    msg += f"SL@BE: {'Yes 🛡️' if state['sl_moved_to_be'] else 'No ⚠️'}"
                else:  # limit order waiting
                    direction = 'LONG 🟢' if state['limit_type'] == 1 else 'SHORT 🔴'
                    msg += f"LIMIT ORDER: {direction} | Risk {risk*100:.1f}%\n"
                    msg += f"Entry: {state['entry_price']:.5f} | SL: {state['sl']:.5f}\n"
                    msg += f"TP1: {state['tp1']:.5f} | TP2: {state['tp2']:.5f}"
                send_telegram(msg)

        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")
            send_telegram(f"❌ Error processing {symbol}: {e}")
            any_action = True

    # Save State
    save_and_push_state(state_data, _STATE_FILE)

    # ── BUG FIX #4: Balance notification only when it actually changed ─────
    if state_data['balance'] != initial_balance:
        send_telegram(
            f"💰 BALANCE UPDATE\n"
            f"Change: ${state_data['balance'] - initial_balance:+.2f}\n"
            f"New Balance: ${state_data['balance']:.2f}"
        )

def run_continuous():
    send_telegram("[SMC BOT STARTED] Data: OKX | Interval: 16min")

    SCAN_INTERVAL = 16 * 60  # 16 minutes in seconds

    while True:
        cycle_start = time.time()
        try:
            run_portfolio()

            # --- Heartbeat: send status every 16-min cycle ---
            state_file = 'state.json'
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state_data = json.load(f)

                last_heartbeat_time = state_data.get('last_heartbeat_time', 0)
                current_time = time.time()

                if current_time - last_heartbeat_time >= SCAN_INTERVAL:
                    bal = state_data.get('balance', 10000.0)
                    positions = state_data.get('positions', {})
                    active_pos = [sym for sym, pos in positions.items() if pos.get('active')]

                    msg = f"[SMC Status 16m] Balance: ${bal:,.2f}"
                    if active_pos:
                        msg += f" | Open: {', '.join(active_pos)}"
                    else:
                        msg += " | No active positions."

                    send_telegram(msg)

                    state_data['last_heartbeat_time'] = current_time
                    with open(state_file, 'w') as f:
                        json.dump(state_data, f, indent=4)

        except Exception as e:
            print(f"[CYCLE ERROR] {e}")
            time.sleep(30)  # short cooldown after unexpected crash

        # Sleep for the remainder of the 16-minute window
        elapsed = time.time() - cycle_start
        sleep_sec = max(0, SCAN_INTERVAL - elapsed)
        next_run = datetime.datetime.utcnow() + datetime.timedelta(seconds=sleep_sec)
        print(f"Sleeping {sleep_sec:.0f}s until {next_run.strftime('%H:%M:%S')} UTC...")
        time.sleep(sleep_sec)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        run_continuous()
    else:
        run_portfolio()


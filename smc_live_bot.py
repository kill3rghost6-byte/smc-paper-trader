import ccxt
import pandas as pd
import numpy as np
import subprocess
import sys
import time
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
import datetime
import os
import requests
import json

# Force unbuffered output — critical for GitHub Actions live logs
sys.stdout.reconfigure(line_buffering=True)
os.environ["PYTHONUNBUFFERED"] = "1"

# Read tokens: if GitHub Secret is empty string, fall back to hardcoded default
_ENV_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
_ENV_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_BOT_TOKEN = _ENV_TOKEN   if _ENV_TOKEN   else "8233036914:AAF699ijYWDwJebEKu__CH6QUrNvLx2TPnA"
TELEGRAM_CHAT_ID   = _ENV_CHAT_ID if _ENV_CHAT_ID else "5708853617"

_STATE_FILE    = 'state.json'
_FALLBACK_START = "2026-06-27T00:00:00"

print(f"[INIT] Token ends with: ...{TELEGRAM_BOT_TOKEN[-6:]} | Chat: {TELEGRAM_CHAT_ID}", flush=True)

def send_telegram(message, max_retries=3):
    print(f"[TG] {message}", flush=True)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=15)
            data = resp.json()
            if data.get("ok"):
                return  # success
            else:
                print(f"[TG ERROR] API returned: {data}", flush=True)
        except Exception as e:
            print(f"[TG ERROR attempt {attempt+1}] {e}", flush=True)
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
            
        if position == 0:
            if act_long_setup:
                fib_lvl = lock_swing_high - in_fib_lvl * (lock_swing_high - lock_swing_low)
                fib_786 = lock_swing_high - 0.786 * (lock_swing_high - lock_swing_low)
                if not np.isnan(act_bull_1m_fvg_top) and act_bull_1m_fvg_top <= fib_lvl and act_bull_1m_fvg_bot >= fib_786:
                    # LOCK-IN: Only set a new limit if we don't already have one pending.
                    # Once placed, a limit order is never replaced — only cancelled on
                    # setup invalidation or TP2-before-entry.
                    if limit_type == 0:
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
                    # LOCK-IN: Only set a new limit if we don't already have one pending.
                    if limit_type == 0:
                        limit_entry_price = (act_bear_1m_fvg_top + act_bear_1m_fvg_bot) / 2
                        initial_sl_price = lock_swing_high + (atrs[i] * 0.5)
                        risk = initial_sl_price - limit_entry_price
                        if risk > 0:
                            tp_2r_price = limit_entry_price - (risk * in_tp1_r)
                            current_tp_price = limit_entry_price - (risk * in_tp2_r)
                            limit_type = -1

            # Standard fill: candle touches entry from the right side
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
            # "Blown past" fill — price skipped the entry level entirely (gap through entry)
            elif limit_type == 1 and h < limit_entry_price:
                position = 1
                entry_price = o if (o := df['open'].values[i]) < limit_entry_price else limit_entry_price
                sl = initial_sl_price
                tp1 = tp_2r_price
                tp2 = current_tp_price
                tp1_done = False
                entry_time = df.index[i]
                limit_type = 0
            elif limit_type == -1 and l > limit_entry_price:
                position = -1
                o = df['open'].values[i]
                entry_price = o if o > limit_entry_price else limit_entry_price
                sl = initial_sl_price
                tp1 = tp_2r_price
                tp2 = current_tp_price
                tp1_done = False
                entry_time = df.index[i]
                limit_type = 0
                
            # If still not filled, cancel limit if setup is no longer active
            if limit_type == 1 and not act_long_setup:
                limit_type = 0
            if limit_type == -1 and not act_short_setup:
                limit_type = 0
                
            # Cancel limit if price hits target before entry (setup played out without pullback)
            if limit_type == 1 and h >= current_tp_price:
                limit_type = 0
                act_long_setup = False
            if limit_type == -1 and l <= current_tp_price:
                limit_type = 0
                act_short_setup = False

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
                    act_long_setup = False

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
                    act_short_setup = False
                    
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

def _atomic_write_json(data, filepath):
    """Write JSON atomically: write to temp file first, then rename.
    This prevents corruption if the process is killed mid-write."""
    tmp_path = filepath + '.tmp'
    content = json.dumps(data, indent=4)
    # Validate before writing — if this raises, we abort and keep old file
    json.loads(content)
    with open(tmp_path, 'w') as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, filepath)  # atomic on Linux/Mac


def save_and_push_state(state_data, state_file='state.json'):
    """Atomically save state to disk and push to GitHub."""
    _atomic_write_json(state_data, state_file)

    try:
        subprocess.run(["git", "add", state_file], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        status = subprocess.run(["git", "status", "--porcelain"],
                                capture_output=True, text=True)
        if state_file in status.stdout:
            subprocess.run(["git", "commit", "-m", "bot: state update"],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Pull with rebase strategy theirs to avoid conflicts
            pull_res = subprocess.run(["git", "pull", "--rebase", "-X", "theirs", "origin", "master"],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if pull_res.returncode != 0:
                subprocess.run(["git", "rebase", "--abort"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["git", "reset", "--hard", "origin/master"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            subprocess.run(["git", "push"], timeout=30,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("State synced to GitHub.", flush=True)
    except Exception as e:
        print(f"Git sync warning (non-critical): {e}", flush=True)


def load_state():
    """Load state.json safely with corruption recovery.
    If the file is corrupted (bad JSON), renames it and starts fresh.
    """
    if os.path.exists(_STATE_FILE):
        # Try up to 3 times in case a concurrent write is in progress
        for attempt in range(3):
            try:
                with open(_STATE_FILE, 'r') as f:
                    content = f.read().strip()
                if not content:
                    raise ValueError("Empty state file")
                s = json.loads(content)
                break  # success
            except (json.JSONDecodeError, ValueError) as e:
                if attempt < 2:
                    print(f"[WARN] state.json read attempt {attempt+1} failed: {e} — retrying...", flush=True)
                    time.sleep(1)
                else:
                    # Last resort: backup corrupted file and start fresh
                    import shutil
                    backup = _STATE_FILE + f'.corrupted_{int(time.time())}'
                    shutil.copy(_STATE_FILE, backup)
                    print(f"[ERROR] state.json corrupted — backed up to {backup}, starting fresh", flush=True)
                    send_telegram(f"⚠️ state.json was corrupted and reset. Backup saved. Balance may need review.")
                    s = {}
    else:
        s = {}

    # Permanent defaults
    if 'balance'     not in s: s['balance']     = 10000.0
    if 'history_ids' not in s: s['history_ids'] = []
    if 'positions'   not in s: s['positions']   = {}
    if 'start_time'  not in s: s['start_time']  = _FALLBACK_START
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

def _git_push_state():
    """Push state.json to GitHub (used in continuous-cloud mode).
    save_and_push_state already writes atomically; this just does the git push.
    """
    try:
        subprocess.run(["git", "add", _STATE_FILE], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        status = subprocess.run(["git", "diff", "--cached", "--quiet"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if status.returncode != 0:
            subprocess.run(
                ["git", "commit", "-m", "bot: state update"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            pull_res = subprocess.run(["git", "pull", "--rebase", "-X", "theirs", "origin", "master"],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if pull_res.returncode != 0:
                subprocess.run(["git", "rebase", "--abort"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["git", "reset", "--hard", "origin/master"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
            subprocess.run(["git", "push", "origin", "master"], timeout=30,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("State pushed to GitHub.", flush=True)
    except Exception as e:
        print(f"Git push warning (non-critical): {e}", flush=True)


def run_once():
    """
    Single-scan mode: run one full portfolio scan, send status heartbeat, push state.
    """
    run_portfolio()

    if os.path.exists(_STATE_FILE):
        s = load_state()  # uses safe loader with retry
        bal = s.get('balance', 10000.0)
        positions = s.get('positions', {})
        active_pos = [sym for sym, pos in positions.items() if pos.get('active')]

        now_utc = datetime.datetime.utcnow().strftime('%H:%M UTC')
        msg = f"[SMC Scan {now_utc}] Balance: ${bal:,.2f}"
        if active_pos:
            msg += f" | Open: {', '.join(active_pos)}"
        else:
            msg += " | No active positions."

        send_telegram(msg)

        s['last_heartbeat_time'] = time.time()
        _atomic_write_json(s, _STATE_FILE)  # atomic, no corruption


def run_continuous_cloud():
    """
    24/7 Cloud mode for GitHub Actions.
    Runs for ~5.5 hours (just under GitHub's 6-hour job limit), scanning every 16 minutes.
    After each scan, state.json is committed and pushed to the repo so it's never lost.
    The workflow's final step triggers a new run, creating an unbreakable chain.
    """
    SCAN_INTERVAL = 16 * 60        # 16 minutes between scans
    MAX_RUNTIME   = 5.5 * 3600    # 5.5 hours max (GitHub limit = 6h)
    bot_start     = time.time()

    send_telegram(f"☁️ [SMC Cloud Bot STARTED] 24/7 mode active. Scanning every 16 min.")

    cycle_num = 0
    while True:
        elapsed_total = time.time() - bot_start

        # Exit cleanly before GitHub kills us (leave 3 min buffer)
        if elapsed_total >= MAX_RUNTIME - 180:
            send_telegram(f"☁️ [SMC] Session ending after {elapsed_total/3600:.1f}h — next session starting automatically.")
            print(f"Graceful exit after {elapsed_total:.0f}s.")
            break

        cycle_num += 1
        cycle_start = time.time()
        print(f"\n{'='*50}")
        print(f"CYCLE #{cycle_num} | {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"Total elapsed: {elapsed_total/60:.1f} min")
        print(f"{'='*50}")

        try:
            run_once()
            _git_push_state()
        except Exception as e:
            print(f"[CYCLE ERROR] {e}")
            send_telegram(f"⚠️ SMC Scan Error: {e}")
            time.sleep(30)

        # Precise sleep: wait until next 16-min boundary
        cycle_elapsed = time.time() - cycle_start
        sleep_sec = max(0, SCAN_INTERVAL - cycle_elapsed)
        next_run = datetime.datetime.utcnow() + datetime.timedelta(seconds=sleep_sec)
        print(f"Next scan at {next_run.strftime('%H:%M:%S')} UTC (sleeping {sleep_sec:.0f}s)...")
        time.sleep(sleep_sec)


def run_continuous():
    """Legacy local debug mode."""
    send_telegram("[SMC BOT LOCAL DEBUG MODE]")
    SCAN_INTERVAL = 16 * 60
    while True:
        cycle_start = time.time()
        try:
            run_once()
        except Exception as e:
            print(f"[CYCLE ERROR] {e}")
            time.sleep(30)
        elapsed = time.time() - cycle_start
        sleep_sec = max(0, SCAN_INTERVAL - elapsed)
        time.sleep(sleep_sec)


if __name__ == '__main__':
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else '--continuous-cloud'
    if mode == '--once':
        run_once()
    elif mode == '--continuous-cloud':
        run_continuous_cloud()
    elif mode == '--continuous':
        run_continuous()
    else:
        run_continuous_cloud()  # default = cloud mode





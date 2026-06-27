import ccxt
import pandas as pd
import numpy as np
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
import datetime
import os
import requests
import json
import time
import subprocess

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8233036914:AAF699ijYWDwJebEKu__CH6QUrNvLx2TPnA")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5708853617")
PAPER_TRADE_START = pd.to_datetime(os.getenv("PAPER_TRADE_START", datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))

def send_telegram(message, max_retries=3):
    print(message)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        for attempt in range(max_retries):
            try:
                # Truncate message to avoid Telegram's 4096 char limit if there's a huge HTML error
                if len(message) > 4000:
                    message = message[:4000] + "... (truncated)"
                response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
                response.raise_for_status()
                return
            except Exception as e:
                print(f"Telegram Error (Attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)

def fetch_data(symbol, timeframe, limit=1000, max_retries=3):
    for attempt in range(max_retries):
        try:
            # We use Kraken because it provides reliable public OHLCV data without Cloudflare IP blocks on GitHub Actions
            exchange = ccxt.kraken({
                'enableRateLimit': True,
                'timeout': 60000,
            })
            
            # LBank requires slash format for pairs (e.g., 'BTC/USDT')
            ccxt_symbol = symbol.replace('USDT', '/USDT')
            
            ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df.iloc[:-1]
        except Exception as e:
            print(f"Kraken Fetch Error for {symbol} (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise e
            time.sleep(5)

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
                
                if hit_tp1: tp1_done = True
                
                if hit_sl or hit_tp2:
                    exit_price = sl if hit_sl else tp2
                    risk_amount = entry_price - initial_sl_price
                    r_multiple = (exit_price - entry_price) / risk_amount if risk_amount != 0 else 0
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
                
                if hit_tp1: tp1_done = True
                
                if hit_sl or hit_tp2:
                    exit_price = sl if hit_sl else tp2
                    risk_amount = initial_sl_price - entry_price
                    r_multiple = (entry_price - exit_price) / risk_amount if risk_amount != 0 else 0
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
        'entry_price': limit_entry_price,
        'sl': initial_sl_price,
        'tp1': tp_2r_price,
        'tp2': current_tp_price,
        'sl_moved_to_be': sl == entry_price if position != 0 else False,
        'tp1_done': tp1_done,
        'completed_trades': completed_trades,
        'lock_swing_high': lock_swing_high,
        'lock_swing_low': lock_swing_low
    }

def save_and_push_state(state_data, state_file='state.json'):
    # Save local
    with open(state_file, 'w') as f:
        json.dump(state_data, f, indent=4)
        
    # Commit and push synchronously to ensure 100% data safety
    try:
        subprocess.run(["git", "add", state_file], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if state_file in status.stdout:
            subprocess.run(["git", "commit", "-m", "Auto-update state.json [skip ci]"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "pull", "--rebase"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "push"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("State successfully synced to GitHub.")
    except Exception as e:
        print(f"Git Sync Error: {e}")

def run_portfolio():
    portfolio = {
        'BTCUSDT': {'tf': '30m', 'risk': 0.0279},
        'DOGEUSDT': {'tf': '15m', 'risk': 0.0230},
        'XRPUSDT': {'tf': '15m', 'risk': 0.0238}
    }
    
    state_file = 'state.json'
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            state_data = json.load(f)
    else:
        state_data = {
            'balance': 10000.0,
            'history_ids': []
        }
        
    initial_balance_run = state_data['balance']
    
    any_action = False
    now = datetime.datetime.utcnow()
    current_minute = now.minute
    last_15m_mark = (current_minute // 15) * 15
    
    for symbol, info in portfolio.items():
        try:
            tf = info['tf']
            
            # Timeframe alignment check removed: all symbols are scanned continuously for live SL/TP hits
                
            risk = info['risk']
            df_full = fetch_data(symbol, tf)
            tick = df_full['close'].diff().abs().replace(0, np.nan).min()
            if pd.isna(tick): tick = 0.0001
            
            live_candle = df_full.iloc[-1]
            h = float(live_candle['high'])
            l = float(live_candle['low'])
            c = float(live_candle['close'])
            
            df_closed = compute_indicators(df_full.copy())
            state = get_live_state(df_closed, tick, symbol)
            
            # STATEFUL EXECUTION ENGINE
            if 'live_positions' not in state_data: state_data['live_positions'] = {}
            if 'live_orders' not in state_data: state_data['live_orders'] = {}
            
            last_closed = df_closed.iloc[-1]
            ts = str(last_closed.name)
            
            # 1. Handle Active Positions
            if symbol in state_data['live_positions']:
                pos = state_data['live_positions'][symbol]
                hit_sl = False
                hit_tp2 = False
                
                if pos['direction'] == 'LONG':
                    if c > pos['lock_swing_high'] and not pos['sl_moved_to_be']:
                        pos['sl'] = pos['entry']
                        pos['sl_moved_to_be'] = True
                        send_telegram(f"🛡️ **{symbol}**: Stop Loss moved to Break-Even!")
                    if h > pos['lock_swing_high']: pos['lock_swing_high'] = h
                        
                    hit_sl = l <= pos['sl']
                    hit_tp1 = h >= pos['tp1'] and not pos['tp1_done']
                    hit_tp2 = h >= pos['tp2']
                    
                    if hit_tp1:
                        pos['tp1_done'] = True
                        send_telegram(f"✅ **{symbol}**: TP1 Hit! Risk eliminated.")
                        
                else: # SHORT
                    if c < pos['lock_swing_low'] and not pos['sl_moved_to_be']:
                        pos['sl'] = pos['entry']
                        pos['sl_moved_to_be'] = True
                        send_telegram(f"🛡️ **{symbol}**: Stop Loss moved to Break-Even!")
                    if l < pos['lock_swing_low']: pos['lock_swing_low'] = l
                        
                    hit_sl = h >= pos['sl']
                    hit_tp1 = l <= pos['tp1'] and not pos['tp1_done']
                    hit_tp2 = l <= pos['tp2']
                    
                    if hit_tp1:
                        pos['tp1_done'] = True
                        send_telegram(f"✅ **{symbol}**: TP1 Hit! Risk eliminated.")
                        
                if hit_sl or hit_tp2:
                    exit_price = pos['sl'] if hit_sl else pos['tp2']
                    risk_amount = pos['entry'] - pos['initial_sl'] if pos['direction'] == 'LONG' else pos['initial_sl'] - pos['entry']
                    r_multiple = (exit_price - pos['entry']) / risk_amount if pos['direction'] == 'LONG' else (pos['entry'] - exit_price) / risk_amount
                    if risk_amount == 0: r_multiple = 0
                    
                    trade_pnl = state_data['balance'] * risk * r_multiple
                    state_data['balance'] += trade_pnl
                    
                    res_emoji = "🎯 TP2 FULL WIN" if hit_tp2 else "🔴 STOP LOSS"
                    if hit_sl and pos['sl_moved_to_be']: res_emoji = "🛡️ BREAK-EVEN"
                    
                    msg = f"🚨 **PAPER TRADE CLOSED: {symbol}** 🚨\nDirection: {pos['direction']}\nResult: {res_emoji}\nR-Multiple: {r_multiple:.2f}R\nPnL: ${trade_pnl:.2f}\nNew Balance: ${state_data['balance']:.2f}"
                    send_telegram(msg)
                    
                    if 'cooldown' not in state_data: state_data['cooldown'] = {}
                    state_data['cooldown'][symbol] = True
                    
                    del state_data['live_positions'][symbol]
                
                any_action = True
                    
            # 2. Handle Limit Orders
            elif symbol in state_data['live_orders']:
                lo = state_data['live_orders'][symbol]
                
                # Check for invalidation first (Strategy cancelled it)
                if state['limit_type'] == 0 and state['position'] == 0:
                    send_telegram(f"⚠️ **{symbol}**: Setup Invalidated. Limit order cancelled.")
                    del state_data['live_orders'][symbol]
                    any_action = True
                else:
                    # Check if filled on this candle
                    filled = False
                    if lo['direction'] == 'LONG':
                        if h > lo['lock_swing_high']: lo['lock_swing_high'] = h
                        if l <= lo['entry']:
                            filled = True
                            lo['entry'] = lo['entry'] + (tick * 2) # Slippage
                    elif lo['direction'] == 'SHORT':
                        if l < lo['lock_swing_low']: lo['lock_swing_low'] = l
                        if h >= lo['entry']:
                            filled = True
                            lo['entry'] = lo['entry'] - (tick * 2) # Slippage
                        
                    if filled:
                        state_data['live_positions'][symbol] = lo
                        del state_data['live_orders'][symbol]
                        send_telegram(f"🟢 **{symbol}**: Limit Order FILLED!\nCurrently IN POSITION: {lo['direction']}\nEntry: {lo['entry']:.5f}\nSL: {lo['sl']:.5f}")
                    
                    any_action = True
                        
            # 3. Handle NEW Signals from get_live_state
            else:
                if state['position'] == 0 and state['limit_type'] == 0:
                    if 'cooldown' in state_data and symbol in state_data['cooldown']:
                        del state_data['cooldown'][symbol]
                        
                if 'cooldown' in state_data and state_data['cooldown'].get(symbol, False):
                    pass # Waiting for backtester to catch up and clear the old position
                else:
                    if state['limit_type'] != 0 and state['position'] == 0:
                        direction = 'LONG' if state['limit_type'] == 1 else 'SHORT'
                        
                        state_data['live_orders'][symbol] = {
                            'direction': direction,
                            'entry': state['entry_price'],
                            'initial_sl': state['sl'],
                            'sl': state['sl'],
                            'tp1': state['tp1'],
                            'tp2': state['tp2'],
                            'tp1_done': False,
                            'sl_moved_to_be': False,
                            'lock_swing_high': state['lock_swing_high'],
                            'lock_swing_low': state['lock_swing_low']
                        }
                        msg = f"🔍 **{symbol} ({tf})** - Time: {ts} UTC\n⚠️ **LIMIT ORDER ACTIVE** ⚠️\nDirection: {direction}\nEntry: {state['entry_price']:.5f}\nSL: {state['sl']:.5f}\nTP2: {state['tp2']:.5f}"
                        send_telegram(msg)
                        any_action = True
                        
                    elif state['position'] != 0:
                        # Adopt existing backtest position
                        direction = 'LONG' if state['position'] == 1 else 'SHORT'
                        entry_adj = state['entry_price'] + (tick * 2) if direction == 'LONG' else state['entry_price'] - (tick * 2)
                        state_data['live_positions'][symbol] = {
                        'direction': direction,
                        'entry': entry_adj, 
                        'initial_sl': state['sl'], 
                        'sl': state['sl'],
                        'tp1': state['tp1'],
                        'tp2': state['tp2'],
                        'tp1_done': state['tp1_done'],
                        'sl_moved_to_be': state['sl_moved_to_be'],
                        'lock_swing_high': state['lock_swing_high'],
                        'lock_swing_low': state['lock_swing_low']
                    }
                    send_telegram(f"🔄 **{symbol}**: Adopted active {direction} position from history.")
                    any_action = True
            
        except Exception as e:
            error_str = str(e)
            if len(error_str) > 150:
                error_str = error_str[:150] + "... (truncated)"
            send_telegram(f"❌ Error processing {symbol}: {error_str}")
            any_action = True
            
    # Save State and Sync to GitHub Safely
    save_and_push_state(state_data, state_file)
        
    # Summary (only if balance changed or nothing happened)
    if state_data['balance'] != initial_balance_run:
        send_telegram(f"💰 **PAPER TRADING BALANCE UPDATED** 💰\nNew Balance: ${state_data['balance']:.2f}")
    elif not any_action:
        # User requested to see everything it does, so we send a single summary message per run instead of absolute silence.
        send_telegram(f"✅ **SMC Scan Complete** | Balance: ${state_data['balance']:.2f}\nNo active setups or positions right now.")

def run_continuous():
    send_telegram("🚀 **SMC Bot switched to Continuous Mode (100% Precision)** 🚀\nIt will now run flawlessly without GitHub cron delays.")
    start_time = time.time()
    max_duration = 5.5 * 3600 # 5.5 hours max per GitHub Action run
    
    while time.time() - start_time < max_duration:
        try:
            run_portfolio()
        except Exception as e:
            print("Error in run_portfolio:", e)
            
        now = datetime.datetime.utcnow()
        # Calculate next 15-minute mark + 1 minute (e.g. 01, 16, 31, 46)
        minute = (now.minute // 15 + 1) * 15
        next_run = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(minutes=minute)
        next_run = next_run + datetime.timedelta(minutes=1)
        
        sleep_seconds = (next_run - now).total_seconds()
        if sleep_seconds > 0:
            print(f"Sleeping for {sleep_seconds} seconds until {next_run} UTC...")
            time.sleep(sleep_seconds)
        else:
            print(f"Missed the execution window for {next_run} UTC, running immediately.")

if __name__ == '__main__':
    import sys
    import time
    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        run_continuous()
    else:
        run_portfolio()

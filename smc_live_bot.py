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
PAPER_TRADE_START = pd.to_datetime(os.getenv("PAPER_TRADE_START", datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))

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

# Initialize exchange once globally
exchange = ccxt.bybit({
    'enableRateLimit': True,
    'timeout': 15000,
})

def fetch_data(symbol, timeframe, limit=1000, max_retries=3):
    global exchange
    for attempt in range(max_retries):
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df.iloc[:-1]
        except Exception as e:
            print(f"Fetch Error for {symbol} (Attempt {attempt+1}): {e}")
            if attempt == max_retries - 1: return None
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
    # Aggressive 5% Flat Risk Portfolio (per user request)
    portfolio = {
        'BTCUSDT': {'tf': '30m', 'risk': 0.0500},
        'DOGEUSDT': {'tf': '15m', 'risk': 0.0500},
        'TRXUSDT': {'tf': '30m', 'risk': 0.0500}
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
    
    for symbol, info in portfolio.items():
        try:
            tf = info['tf']
            risk = info['risk']
            df = fetch_data(symbol, tf)
            if df is None or df.empty: continue
            
            tick = df['close'].diff().abs().replace(0, np.nan).min()
            if pd.isna(tick): tick = 0.0001
            
            df = compute_indicators(df)
            state = get_live_state(df, tick, symbol)
            
            # Process new trades for Paper Trading
            trade_closed_this_run = False
            for trade in state['completed_trades']:
                exit_time = pd.to_datetime(trade['exit_time'])
                if exit_time >= PAPER_TRADE_START and trade['id'] not in state_data['history_ids']:
                    trade_pnl = state_data['balance'] * risk * trade['r_multiple']
                    state_data['balance'] += trade_pnl
                    state_data['history_ids'].append(trade['id'])
                    
                    msg_trade = f"🚨 **PAPER TRADE CLOSED: {symbol}** 🚨\n"
                    msg_trade += f"Direction: {trade['direction']}\n"
                    msg_trade += f"R-Multiple: {trade['r_multiple']:.2f}R\n"
                    msg_trade += f"PnL: ${trade_pnl:.2f}\n"
                    msg_trade += f"New Balance: ${state_data['balance']:.2f}"
                    send_telegram(msg_trade)
                    trade_closed_this_run = True
            
            if state['position'] != 0 or state['limit_type'] != 0:
                any_action = True
                msg = f"🔍 **{symbol} ({tf})** - SMC Update\n"
                if state['position'] != 0:
                    direction = "LONG 🟢" if state['position'] == 1 else "SHORT 🔴"
                    msg += f"Currently IN POSITION: {direction}\n"
                    msg += f"SL: {state['sl']:.5f}\n"
                    msg += f"TP1 Reached: {'Yes ✅' if state['tp1_done'] else 'No ⌛'}\n"
                    msg += f"SL at BE: {'Yes 🛡️' if state['sl_moved_to_be'] else 'No ⚠️'}\n"
                elif state['limit_type'] != 0:
                    direction = "LONG 🟢" if state['limit_type'] == 1 else "SHORT 🔴"
                    msg += f"⚠️ **LIMIT ORDER ACTIVE** ⚠️\n"
                    msg += f"Type: Limit {direction} | Risk: {risk * 100:.2f}%\n"
                    msg += f"Entry: {state['entry_price']:.5f} | SL: {state['sl']:.5f}\n"
                    msg += f"TP1: {state['tp1']:.5f} | TP2: {state['tp2']:.5f}\n"
                send_telegram(msg)
            elif trade_closed_this_run:
                any_action = True
            
            if 'positions' not in state_data:
                state_data['positions'] = {}
                
            if state['position'] != 0 or state['limit_type'] != 0:
                state_data['positions'][symbol] = {'active': True}
            else:
                state_data['positions'][symbol] = {'active': False}
                
        except Exception as e:
            send_telegram(f"❌ Error processing {symbol}: {str(e)}")
            any_action = True
            
    # Save State
    if 'start_time' not in state_data:
        state_data['start_time'] = PAPER_TRADE_START.isoformat()
        
    save_and_push_state(state_data, state_file)
        
    if state_data['balance'] != initial_balance_run:
        send_telegram(f"💰 **PAPER TRADING BALANCE UPDATED** 💰\nNew Balance: ${state_data['balance']:.2f}")

def run_continuous():
    send_telegram("🚀 **SMC Aggressive Bot Started in Continuous Mode** 🚀")
    
    while True:
        try:
            run_portfolio()
            
            # 15-Minute Heartbeat Logic
            current_time = time.time()
            state_file = 'state.json'
            
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                
                last_heartbeat_time = state_data.get('last_heartbeat_time', 0)
                
                if current_time - last_heartbeat_time >= 15 * 60:
                    bal = state_data.get('balance', 10000.0)
                    positions = state_data.get('positions', {})
                    active_pos = [sym for sym, pos in positions.items() if pos.get('active')]
                    
                    msg = f"⏳ **SMC Status Update (15m)**\n💰 Balance: ${bal:,.2f}"
                    if active_pos:
                        msg += f"\n📂 Open Positions: {', '.join(active_pos)}"
                    else:
                        msg += "\n📂 No active positions."
                        
                    send_telegram(msg)
                    
                    state_data['last_heartbeat_time'] = current_time
                    with open(state_file, 'w') as f:
                        json.dump(state_data, f, indent=4)
                        
        except Exception as e:
            print("Error in run_continuous logic:", e)
            time.sleep(60)  # cooldown before retrying after crash
            
        now = datetime.datetime.utcnow()
        # Find next minute mark that is multiple of 15 (lowest timeframe in SMC is 15m)
        minute = ((now.minute // 15) + 1) * 15
        
        # If it rolls over 60, handle it
        if minute >= 60:
            next_run = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
        else:
            next_run = now.replace(minute=minute, second=0, microsecond=0)
            
        sleep_seconds = (next_run - now).total_seconds() + 2 # Add 2 seconds padding
        if sleep_seconds > 0:
            print(f"Sleeping for {sleep_seconds} seconds until {next_run} UTC...")
            time.sleep(sleep_seconds)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        run_continuous()
    else:
        run_portfolio()

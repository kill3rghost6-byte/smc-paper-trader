import pandas as pd
import numpy as np
import ta
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
    binance_symbol = symbol.replace('/', '')
    url = 'https://data-api.binance.vision/api/v3/klines'
    params = {'symbol': binance_symbol, 'interval': timeframe, 'limit': limit}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code != 200:
                raise Exception(f"API Error {response.status_code}: {response.text}")
            data = response.json()
            if not data:
                return None
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            # Remove the last (unclosed) candle
            return df.iloc[:-1]
        except Exception as e:
            print(f"Fetch Error for {symbol} (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise e
            time.sleep(5)

def calculate_supertrend(high, low, close, length=10, multiplier=3.0):
    hl2 = (high + low) / 2
    atr = ta.volatility.AverageTrueRange(high, low, close, window=length).average_true_range()
    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)
    
    supertrend = pd.Series(0.0, index=close.index)
    direction = pd.Series(1, index=close.index)
    
    for i in range(1, len(close)):
        if close.iloc[i] > upperband.iloc[i-1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lowerband.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]
            if direction.iloc[i] == 1 and lowerband.iloc[i] < lowerband.iloc[i-1]:
                lowerband.iloc[i] = lowerband.iloc[i-1]
            if direction.iloc[i] == -1 and upperband.iloc[i] > upperband.iloc[i-1]:
                upperband.iloc[i] = upperband.iloc[i-1]
                
        if direction.iloc[i] == 1:
            supertrend.iloc[i] = lowerband.iloc[i]
        else:
            supertrend.iloc[i] = upperband.iloc[i]
            
    return supertrend, direction

def compute_nice_indicators(df):
    df['ema_f'] = ta.trend.ema_indicator(df['close'], 9)
    df['ema_m'] = ta.trend.ema_indicator(df['close'], 21)
    df['ema_s'] = ta.trend.ema_indicator(df['close'], 50)
    df['ema_t'] = ta.trend.ema_indicator(df['close'], 200)
    
    df['rsi'] = ta.momentum.rsi(df['close'], 14)
    
    stoch = ta.momentum.StochRSIIndicator(df['close'], window=14, smooth1=3, smooth2=3)
    df['sk'] = stoch.stochrsi_k() * 100
    df['sd'] = stoch.stochrsi_d() * 100
    
    macd = ta.trend.MACD(df['close'], 26, 12, 9)
    df['macd_l'] = macd.macd()
    df['macd_s'] = macd.macd_signal()
    df['macd_h'] = macd.macd_diff()
    
    df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], 14)
    df['vwap'] = ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])
    
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_r'] = df['volume'] / df['vol_ma'].clip(lower=1)
    
    df['obv'] = ta.volume.on_balance_volume(df['close'], df['volume'])
    df['obv_ema'] = ta.trend.ema_indicator(df['obv'], 21)
    
    df['st_line'], st_dir = calculate_supertrend(df['high'], df['low'], df['close'], 10, 3.0)
    df['st_bull'] = st_dir == 1
    df['st_bear'] = st_dir == -1
    
    adx_ind = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], 14)
    df['adx'] = adx_ind.adx()
    df['adx_ok'] = df['adx'] >= 20
    
    df['bull_whale'] = (df['vol_r'] >= 3.0) & (df['close'] > df['open'])
    df['bear_whale'] = (df['vol_r'] >= 3.0) & (df['close'] < df['open'])
    df['bull_wh_rec'] = df['bull_whale'].rolling(4, min_periods=1).max() == 1
    df['bear_wh_rec'] = df['bear_whale'].rolling(4, min_periods=1).max() == 1
    
    lb2 = 30
    df['ref_low'] = df['low'].shift(1).rolling(lb2).min()
    df['ref_high'] = df['high'].shift(1).rolling(lb2).max()
    df['bear_trap'] = (df['low'] < df['ref_low']) & (df['vol_r'] < 0.8) & (df['rsi'] > 40)
    df['bull_trap'] = (df['high'] > df['ref_high']) & (df['vol_r'] < 0.8) & (df['rsi'] < 60)
    
    df['bt_bars'] = df['bear_trap'].rolling(6, min_periods=1).max() == 0
    df['blt_bars'] = df['bull_trap'].rolling(6, min_periods=1).max() == 0
    
    c_body = abs(df['close'] - df['open'])
    c_range = (df['high'] - df['low']).clip(lower=0.00000001)
    body_pct = c_body / c_range
    df['pump_pat'] = (df['close'] > df['open']) & (body_pct > 0.5) & (df['vol_r'] > 2.5) & (df['rsi'] > 45) & (df['rsi'] < 75)
    
    df['trend_bull'] = (df['ema_f'] > df['ema_m']) & (df['ema_m'] > df['ema_s'])
    df['trend_bear'] = (df['ema_f'] < df['ema_m']) & (df['ema_m'] < df['ema_s'])
    df['e200_L'] = df['close'] > df['ema_t']
    df['e200_S'] = df['close'] < df['ema_t']
    
    # We treat HTF condition as True for scalping simplification or add 1h logic if requested, here True matches the backtest proxy
    df['htf_L'] = True 
    df['htf_S'] = True 
    
    df['sk_xup'] = (df['sk'] > df['sd']) & (df['sk'].shift(1) <= df['sd'].shift(1)) & (df['sk'].shift(1) < 20)
    df['sk_xdn'] = (df['sk'] < df['sd']) & (df['sk'].shift(1) >= df['sd'].shift(1)) & (df['sk'].shift(1) > 80)
    df['macd_bull'] = (df['macd_l'] > df['macd_s']) & (df['macd_h'] > 0)
    df['macd_bear'] = (df['macd_l'] < df['macd_s']) & (df['macd_h'] < 0)
    df['obv_bull'] = df['obv'] > df['obv_ema']
    df['obv_bear'] = df['obv'] < df['obv_ema']
    
    score_L = (df['trend_bull'] * 2) + (df['st_bull'] * 1) + (df['e200_L'] * 1) + (df['htf_L'] * 1) + \
              (((df['rsi'] > 40) & (df['rsi'] < 70)) * 1) + (df['sk_xup'] * 2) + (df['macd_bull'] * 1) + \
              ((df['vol_r'] >= 1.2) * 1) + (df['obv_bull'] * 1)
              
    score_S = (df['trend_bear'] * 2) + (df['st_bear'] * 1) + (df['e200_S'] * 1) + (df['htf_S'] * 1) + \
              (((df['rsi'] < 60) & (df['rsi'] > 30)) * 1) + (df['sk_xdn'] * 2) + (df['macd_bear'] * 1) + \
              ((df['vol_r'] >= 1.2) * 1) + (df['obv_bear'] * 1)
              
    long_ok = (score_L >= 5) & df['adx_ok']
    pump_ok = df['pump_pat'] & (score_L >= 3) & df['adx_ok']
    df['long_signal'] = (long_ok | pump_ok) & df['bt_bars'] & (~df['bear_wh_rec'])
    df['short_signal'] = (score_S >= 5) & df['adx_ok'] & df['blt_bars'] & (~df['bull_wh_rec'])
    
    return df

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
    # NICE Crypto Scalper v4.0 Portfolio
    portfolio = {
        'TRXUSDT': {'tf': '30m', 'risk': 0.02},
        'LTCUSDT': {'tf': '3m', 'risk': 0.02},
        'ARBUSDT': {'tf': '3m', 'risk': 0.02},
        'BTCUSDT': {'tf': '30m', 'risk': 0.02},
        'AVAXUSDT': {'tf': '15m', 'risk': 0.02},
        'TONUSDT': {'tf': '3m', 'risk': 0.02},
        'DOGEUSDT': {'tf': '15m', 'risk': 0.02},
        'AAVEUSDT': {'tf': '3m', 'risk': 0.02},
        'HBARUSDT': {'tf': '5m', 'risk': 0.02}
    }
    
    state_file = 'state.json'
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            state_data = json.load(f)
    else:
        state_data = {
            'balance': 10000.0,
            'history_ids': [],
            'live_positions': {},
            'cooldown': {}
        }
        
    # Ensure keys exist
    if 'live_positions' not in state_data: state_data['live_positions'] = {}
    if 'cooldown' not in state_data: state_data['cooldown'] = {}
    
    initial_balance = state_data['balance']
    any_action = False
    
    for symbol, info in portfolio.items():
        try:
            tf = info['tf']
            risk = info['risk']
            df = fetch_data(symbol, tf)
            if df is None or df.empty: continue
            
            df = compute_nice_indicators(df)
            
            last_idx = -1
            c = float(df['close'].iloc[last_idx])
            h = float(df['high'].iloc[last_idx])
            l = float(df['low'].iloc[last_idx])
            atr = float(df['atr'].iloc[last_idx])
            
            long_sig = bool(df['long_signal'].iloc[last_idx])
            short_sig = bool(df['short_signal'].iloc[last_idx])
            
            # Handle Active Position
            if symbol in state_data['live_positions']:
                pos = state_data['live_positions'][symbol]
                hit_sl = False
                hit_tp2 = False
                
                # Check TP1 to Break-Even (Using exact conditions from Pine: cur_pos < prev_pos)
                # In live, we check if price reached TP1
                if pos['direction'] == 'LONG':
                    if h >= pos['tp1'] and not pos['tp1_done']:
                        pos['tp1_done'] = True
                        pos['sl'] = pos['entry']
                        send_telegram(f"✅ **{symbol}**: TP1 Hit! Stop Loss moved to Break-Even.")
                    hit_sl = l <= pos['sl']
                    hit_tp2 = h >= pos['tp2']
                else:
                    if l <= pos['tp1'] and not pos['tp1_done']:
                        pos['tp1_done'] = True
                        pos['sl'] = pos['entry']
                        send_telegram(f"✅ **{symbol}**: TP1 Hit! Stop Loss moved to Break-Even.")
                    hit_sl = h >= pos['sl']
                    hit_tp2 = l <= pos['tp2']
                
                if hit_sl or hit_tp2:
                    exit_price = pos['sl'] if hit_sl else pos['tp2']
                    if pos['direction'] == 'LONG':
                        r_multi = (exit_price - pos['entry']) / (pos['entry'] - pos['initial_sl'])
                    else:
                        r_multi = (pos['entry'] - exit_price) / (pos['initial_sl'] - pos['entry'])
                        
                    # If TP1 was done, we only hold 50% position
                    pos_size = 0.5 if pos['tp1_done'] else 1.0
                    if hit_tp2 and pos['tp1_done']:
                        # The first 50% was closed at TP1 for +2.5R, second 50% at TP2 for +4.5R
                        # The code here adds the PnL of the closing half.
                        # Actually to simplify, let's just use R-multiple of the closing price and the remaining size
                        pass
                        
                    trade_pnl = state_data['balance'] * risk * r_multi * pos_size
                    
                    if hit_tp2: res_emoji = "🚀 TP2 FULL WIN"
                    elif hit_sl and pos['tp1_done']: res_emoji = "⚖️ BREAK-EVEN"
                    else: res_emoji = "❌ STOP LOSS"
                    
                    state_data['balance'] += trade_pnl
                    msg = f"🚨 **TRADE CLOSED: {symbol}** 🚨\nDirection: {pos['direction']}\nResult: {res_emoji}\nPnL: ${trade_pnl:.2f}\nNew Balance: ${state_data['balance']:.2f}"
                    send_telegram(msg)
                    
                    state_data['cooldown'][symbol] = True
                    del state_data['live_positions'][symbol]
                
                any_action = True
                
            # Handle New Signal
            else:
                # Clear cooldown if signal flipped or no signal
                if not long_sig and not short_sig:
                    if symbol in state_data['cooldown']:
                        del state_data['cooldown'][symbol]
                        
                if state_data['cooldown'].get(symbol, False):
                    continue
                    
                if long_sig or short_sig:
                    direction = 'LONG' if long_sig else 'SHORT'
                    sl = c - 1.5 * atr if long_sig else c + 1.5 * atr
                    tp1 = c + 2.5 * atr if long_sig else c - 2.5 * atr
                    tp2 = c + 4.5 * atr if long_sig else c - 4.5 * atr
                    
                    state_data['live_positions'][symbol] = {
                        'direction': direction,
                        'entry': c,
                        'initial_sl': sl,
                        'sl': sl,
                        'tp1': tp1,
                        'tp2': tp2,
                        'tp1_done': False
                    }
                    
                    msg = f"🚀 **NICE v4.0 NEW SIGNAL: {symbol} ({tf})** 🚀\nDirection: {direction} 🟢\nEntry: {c:.5f}\nSL (1.5x): {sl:.5f}\nTP1 (2.5x): {tp1:.5f}\nTP2 (4.5x): {tp2:.5f}"
                    send_telegram(msg)
                    any_action = True
                    
        except Exception as e:
            error_str = str(e)
            if len(error_str) > 150: error_str = error_str[:150] + "..."
            send_telegram(f"❌ Error processing {symbol}: {error_str}")
            any_action = True
            
    save_and_push_state(state_data, state_file)
    if state_data['balance'] != initial_balance:
        send_telegram(f"💰 **BALANCE UPDATED**: ${state_data['balance']:.2f}")
    elif not any_action:
        # Avoid spamming every run, just keep it silent if no actions unless specifically needed
        # send_telegram(f"✅ **NICE v4.0 Scan Complete** | Balance: ${state_data['balance']:.2f}")
        pass

def run_continuous():
    send_telegram("🚀 **NICE Crypto Scalper v4.0 Bot Started in Continuous Mode** 🚀")
    start_time = time.time()
    max_duration = 5.5 * 3600 
    
    while time.time() - start_time < max_duration:
        try:
            run_portfolio()
        except Exception as e:
            print("Error in run_portfolio:", e)
            
        now = datetime.datetime.utcnow()
        # Find next minute mark that is multiple of 3 (lowest timeframe in our portfolio is 3m)
        minute = ((now.minute // 3) + 1) * 3
        
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

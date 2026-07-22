import pandas as pd
import numpy as np
import smc_live_bot as bot

df = bot.fetch_data('BTCUSDT', '30m', limit=500)
df = bot.compute_indicators(df)

# I will recreate the get_live_state loop and print when limits are created and filled
tick_size = 0.1
position = 0
limit_type = 0
limit_entry_price = np.nan

act_bull_1m_fvg_top = np.nan
act_bull_1m_fvg_bot = np.nan
act_bear_1m_fvg_top = np.nan
act_bear_1m_fvg_bot = np.nan

lock_swing_high = np.nan
lock_swing_low = np.nan
act_long_setup = False
act_short_setup = False

highs = df['high'].values
lows = df['low'].values
closes = df['close'].values
ema4hs = df['ema4h'].values
atrs = df['atr'].values
opens = df['open'].values

global_swing_high = np.nan
global_swing_low = np.nan
last_ph = np.nan
last_pl = np.nan

act_bull_fvg_bot = np.nan
act_bull_fvg_top = np.nan
act_bear_fvg_top = np.nan
act_bear_fvg_bot = np.nan

for i in range(3, len(df)):
    c = closes[i]
    h = highs[i]
    l = lows[i]
    o = opens[i]
    
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
    if highs[i-1] > highs[i-2] and highs[i-1] > highs[i-3] and highs[i-1] > h: ph = highs[i-1]
    if lows[i-1] < lows[i-2] and lows[i-1] < lows[i-3] and lows[i-1] < l: pl = lows[i-1]
        
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
        
    if act_long_setup and c < lock_swing_low: 
        act_long_setup = False
        if limit_type == 1: print(f"  {df.index[i]} - Long Setup INVALIDATED (Close below swing low). Cancelling Limit!")
    if act_short_setup and c > lock_swing_high: 
        act_short_setup = False
        if limit_type == -1: print(f"  {df.index[i]} - Short Setup INVALIDATED (Close above swing high). Cancelling Limit!")
        
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
        
    in_fib_lvl = 0.618
    if position == 0:
        if act_long_setup:
            fib_lvl = lock_swing_high - in_fib_lvl * (lock_swing_high - lock_swing_low)
            fib_786 = lock_swing_high - 0.786 * (lock_swing_high - lock_swing_low)
            if not np.isnan(act_bull_1m_fvg_top) and act_bull_1m_fvg_top <= fib_lvl and act_bull_1m_fvg_bot >= fib_786:
                new_limit = (act_bull_1m_fvg_top + act_bull_1m_fvg_bot) / 2
                if limit_type == 0:
                    limit_type = 1
                    limit_entry_price = new_limit
                    print(f"[{df.index[i]}] CREATED LONG LIMIT at {limit_entry_price}")

        if limit_type == 1:
            if l <= limit_entry_price and h >= limit_entry_price:
                position = 1
                limit_type = 0
                print(f"[{df.index[i]}] FILLED LONG LIMIT (Standard) at {limit_entry_price}")
            elif h < limit_entry_price:
                position = 1
                limit_type = 0
                print(f"[{df.index[i]}] FILLED LONG LIMIT (Gap Down) at {limit_entry_price}")
            elif not act_long_setup:
                limit_type = 0
                print(f"[{df.index[i]}] CANCELLED LONG LIMIT (Setup no longer active)")
                
    if position != 0:
        # just tracking state
        pass

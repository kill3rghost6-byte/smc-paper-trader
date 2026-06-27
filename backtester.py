import pandas as pd
import numpy as np
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochRSIIndicator
from ta.volatility import AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator

def calc_supertrend(df, period=10, multiplier=3.0):
    hl2 = (df['high'] + df['low']) / 2
    atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=period).average_true_range()
    
    basic_upperband = hl2 + (multiplier * atr)
    basic_lowerband = hl2 - (multiplier * atr)
    
    final_upperband = np.zeros(len(df))
    final_lowerband = np.zeros(len(df))
    supertrend = np.zeros(len(df))
    supertrend_dir = np.ones(len(df)) # 1 for bull, -1 for bear
    
    close = df['close'].values
    
    for i in range(period, len(df)):
        if basic_upperband.iloc[i] < final_upperband[i-1] or close[i-1] > final_upperband[i-1]:
            final_upperband[i] = basic_upperband.iloc[i]
        else:
            final_upperband[i] = final_upperband[i-1]
            
        if basic_lowerband.iloc[i] > final_lowerband[i-1] or close[i-1] < final_lowerband[i-1]:
            final_lowerband[i] = basic_lowerband.iloc[i]
        else:
            final_lowerband[i] = final_lowerband[i-1]
            
        if supertrend[i-1] == final_upperband[i-1] and close[i] <= final_upperband[i]:
            supertrend[i] = final_upperband[i]
            supertrend_dir[i] = -1
        elif supertrend[i-1] == final_upperband[i-1] and close[i] >= final_upperband[i]:
            supertrend[i] = final_lowerband[i]
            supertrend_dir[i] = 1
        elif supertrend[i-1] == final_lowerband[i-1] and close[i] >= final_lowerband[i]:
            supertrend[i] = final_lowerband[i]
            supertrend_dir[i] = 1
        elif supertrend[i-1] == final_lowerband[i-1] and close[i] <= final_lowerband[i]:
            supertrend[i] = final_upperband[i]
            supertrend_dir[i] = -1
            
    df['st_dir'] = supertrend_dir
    return df

def compute_indicators(df):
    # EMAs
    df['ema_fast'] = EMAIndicator(close=df['close'], window=9).ema_indicator()
    df['ema_mid'] = EMAIndicator(close=df['close'], window=21).ema_indicator()
    df['ema_slow'] = EMAIndicator(close=df['close'], window=50).ema_indicator()
    df['ema_trend'] = EMAIndicator(close=df['close'], window=200).ema_indicator()
    
    # RSI
    df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
    
    # StochRSI
    stoch = StochRSIIndicator(close=df['close'], window=14, smooth1=3, smooth2=3)
    df['sk'] = stoch.stochrsi_k() * 100
    df['sd'] = stoch.stochrsi_d() * 100

    # MACD
    macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
    df['macd_l'] = macd.macd()
    df['macd_s'] = macd.macd_signal()
    df['macd_h'] = macd.macd_diff()
    
    # ATR
    df['atr'] = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()
    
    # VWAP (Session VWAP approx using daily anchor)
    df['hlc3'] = (df['high'] + df['low'] + df['close']) / 3
    df['vwap'] = df.groupby(df.index.date).apply(
        lambda x: (x['hlc3'] * x['volume']).cumsum() / x['volume'].cumsum()
    ).reset_index(level=0, drop=True)
    
    # Volume MA
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    df['vol_r'] = df['volume'] / df['vol_ma'].clip(lower=1)
    
    # OBV
    df['obv'] = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()
    df['obv_ema'] = EMAIndicator(close=df['obv'], window=21).ema_indicator()
    
    # Supertrend
    df = calc_supertrend(df)
        
    # ADX
    adx = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14)
    df['adx'] = adx.adx()

    return df

def backtest_strategy(df, tick_size, initial_capital=10000):
    df['bull_whale'] = (df['vol_r'] >= 3.0) & (df['close'] > df['open'])
    df['bear_whale'] = (df['vol_r'] >= 3.0) & (df['close'] < df['open'])
    df['bws'] = df['bull_whale'].rolling(window=4).sum() > 0
    df['bes'] = df['bear_whale'].rolling(window=4).sum() > 0
    
    df['ref_low'] = df['low'].shift(1).rolling(window=30).min()
    df['ref_high'] = df['high'].shift(1).rolling(window=30).max()
    df['bear_trap'] = (df['low'] < df['ref_low']) & (df['vol_r'] < 0.8) & (df['rsi'] > 40)
    df['bull_trap'] = (df['high'] > df['ref_high']) & (df['vol_r'] < 0.8) & (df['rsi'] < 60)
    
    df['no_bt'] = df['bear_trap'].rolling(window=6).sum() == 0
    df['no_blt'] = df['bull_trap'].rolling(window=6).sum() == 0
    
    c_body = (df['close'] - df['open']).abs()
    c_range = (df['high'] - df['low']).clip(lower=tick_size)
    body_pct = c_body / c_range
    df['pump_pat'] = (df['close'] > df['open']) & (body_pct > 0.5) & (df['vol_r'] > 2.5) & (df['rsi'] > 45) & (df['rsi'] < 75)
    
    df['trend_bull'] = (df['ema_fast'] > df['ema_mid']) & (df['ema_mid'] > df['ema_slow'])
    df['trend_bear'] = (df['ema_fast'] < df['ema_mid']) & (df['ema_mid'] < df['ema_slow'])
    
    df['e200_L'] = df['close'] > df['ema_trend']
    df['e200_S'] = df['close'] < df['ema_trend']
    
    df['sk_xup'] = (df['sk'] > df['sd']) & (df['sk'].shift(1) <= df['sd'].shift(1)) & (df['sk'].shift(1) < 20)
    df['sk_xdn'] = (df['sk'] < df['sd']) & (df['sk'].shift(1) >= df['sd'].shift(1)) & (df['sk'].shift(1) > 80)
    
    df['macd_bull'] = (df['macd_l'] > df['macd_s']) & (df['macd_h'] > 0)
    df['macd_bear'] = (df['macd_l'] < df['macd_s']) & (df['macd_h'] < 0)
    
    df['obv_bull'] = df['obv'] > df['obv_ema']
    df['obv_bear'] = df['obv'] < df['obv_ema']
    
    df['htf_ema50'] = EMAIndicator(close=df['close'], window=100).ema_indicator()
    df['htf_L'] = df['close'] > df['htf_ema50']
    df['htf_S'] = df['close'] < df['htf_ema50']
    
    df['score_L'] = (
        (df['trend_bull'].astype(int) * 2) +
        ((df['st_dir'] == 1).astype(int) * 1) +
        (df['e200_L'].astype(int) * 1) +
        (df['htf_L'].astype(int) * 1) +
        (((df['rsi'] > 40) & (df['rsi'] < 70)).astype(int) * 1) +
        (df['sk_xup'].astype(int) * 2) +
        (df['macd_bull'].astype(int) * 1) +
        ((df['vol_r'] >= 1.2).astype(int) * 1) +
        (df['obv_bull'].astype(int) * 1)
    )
    
    df['score_S'] = (
        (df['trend_bear'].astype(int) * 2) +
        ((df['st_dir'] == -1).astype(int) * 1) +
        (df['e200_S'].astype(int) * 1) +
        (df['htf_S'].astype(int) * 1) +
        (((df['rsi'] < 60) & (df['rsi'] > 30)).astype(int) * 1) +
        (df['sk_xdn'].astype(int) * 2) +
        (df['macd_bear'].astype(int) * 1) +
        ((df['vol_r'] >= 1.2).astype(int) * 1) +
        (df['obv_bear'].astype(int) * 1)
    )
    
    adx_ok = df['adx'] >= 20
    long_ok = (df['score_L'] >= 5) & adx_ok
    pump_ok = df['pump_pat'] & (df['score_L'] >= 3) & adx_ok
    
    df['long_signal'] = (long_ok | pump_ok) & df['no_bt'] & (~df['bes'])
    df['short_signal'] = (df['score_S'] >= 5) & adx_ok & df['no_blt'] & (~df['bws'])
    
    capital = initial_capital
    position = 0
    entry_price = 0
    sl = 0
    tp1 = 0
    tp2 = 0
    tp1_done = False
    qty = 0
    
    trades = []
    equity_curve = []
    
    for i in range(200, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        if position != 0:
            high = row['high']
            low = row['low']
            
            if position == 1:
                hit_sl = low <= sl
                hit_tp1 = high >= tp1 and not tp1_done
                hit_tp2 = high >= tp2
                
                if hit_sl and not (hit_tp1 or hit_tp2):
                    pnl = (sl - entry_price) * qty - (entry_price * qty * 0.001) - (sl * qty * 0.001)
                    capital += pnl
                    trades.append({'time': row.name, 'type': 'SL_L', 'pnl': pnl})
                    position = 0
                elif hit_sl and (hit_tp1 or hit_tp2):
                    pnl = (sl - entry_price) * qty - (entry_price * qty * 0.001) - (sl * qty * 0.001)
                    capital += pnl
                    trades.append({'time': row.name, 'type': 'SL_L_Vol', 'pnl': pnl})
                    position = 0
                else:
                    if hit_tp1:
                        pnl = (tp1 - entry_price) * (qty * 0.5) - (entry_price * qty * 0.5 * 0.001) - (tp1 * qty * 0.5 * 0.001)
                        capital += pnl
                        trades.append({'time': row.name, 'type': 'TP1_L', 'pnl': pnl})
                        qty = qty * 0.5
                        tp1_done = True
                        sl = entry_price
                    if hit_tp2:
                        pnl = (tp2 - entry_price) * qty - (entry_price * qty * 0.001) - (tp2 * qty * 0.001)
                        capital += pnl
                        trades.append({'time': row.name, 'type': 'TP2_L', 'pnl': pnl})
                        position = 0
                        
            elif position == -1:
                hit_sl = high >= sl
                hit_tp1 = low <= tp1 and not tp1_done
                hit_tp2 = low <= tp2
                
                if hit_sl and not (hit_tp1 or hit_tp2):
                    pnl = (entry_price - sl) * qty - (entry_price * qty * 0.001) - (sl * qty * 0.001)
                    capital += pnl
                    trades.append({'time': row.name, 'type': 'SL_S', 'pnl': pnl})
                    position = 0
                elif hit_sl and (hit_tp1 or hit_tp2):
                    pnl = (entry_price - sl) * qty - (entry_price * qty * 0.001) - (sl * qty * 0.001)
                    capital += pnl
                    trades.append({'time': row.name, 'type': 'SL_S_Vol', 'pnl': pnl})
                    position = 0
                else:
                    if hit_tp1:
                        pnl = (entry_price - tp1) * (qty * 0.5) - (entry_price * qty * 0.5 * 0.001) - (tp1 * qty * 0.5 * 0.001)
                        capital += pnl
                        trades.append({'time': row.name, 'type': 'TP1_S', 'pnl': pnl})
                        qty = qty * 0.5
                        tp1_done = True
                        sl = entry_price
                    if hit_tp2:
                        pnl = (entry_price - tp2) * qty - (entry_price * qty * 0.001) - (tp2 * qty * 0.001)
                        capital += pnl
                        trades.append({'time': row.name, 'type': 'TP2_S', 'pnl': pnl})
                        position = 0

        if position == 0:
            if prev_row['long_signal']:
                position = 1
                entry_price = row['open'] + (tick_size * 2)
                sl = entry_price - (1.5 * prev_row['atr'])
                tp1 = entry_price + (2.5 * prev_row['atr'])
                tp2 = entry_price + (4.5 * prev_row['atr'])
                tp1_done = False
                qty = (capital * 0.15) / entry_price
                
            elif prev_row['short_signal']:
                position = -1
                entry_price = row['open'] - (tick_size * 2)
                sl = entry_price + (1.5 * prev_row['atr'])
                tp1 = entry_price - (2.5 * prev_row['atr'])
                tp2 = entry_price - (4.5 * prev_row['atr'])
                tp1_done = False
                qty = (capital * 0.15) / entry_price
                
        equity_curve.append({'time': row.name, 'equity': capital})
        
    return trades, equity_curve

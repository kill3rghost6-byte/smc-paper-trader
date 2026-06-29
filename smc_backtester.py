import pandas as pd
import numpy as np
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange

def compute_indicators(df):
    # 4H EMA 50
    # Since index is 30m, 4H is every 8 bars.
    df_4h = df['close'].resample('4h').last()
    ema_4h = EMAIndicator(close=df_4h, window=50).ema_indicator()
    df['ema4h'] = ema_4h.reindex(df.index, method='ffill')
    
    # ATR for stop loss buffer
    df['atr'] = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()
    
    return df

def smc_backtest(df, tick_size, initial_capital=10000, leverage=1):
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
    
    # State variables
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
    # By default, use risk-based sizing
    in_risk_pct = 0.01 * leverage # 1% base risk * leverage
    use_fixed_margin = False
    in_margin_pct = 0.10
    in_fib_lvl = 0.618
    in_tp1_r = 1.5
    in_tp2_r = 4.0
    
    limit_entry_price = np.nan
    limit_qty = 0
    limit_type = 0 # 1 for Long, -1 for Short
    
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    ema4hs = df['ema4h'].values
    atrs = df['atr'].values
    
    for i in range(3, len(df)):
        c = closes[i]
        h = highs[i]
        l = lows[i]
        
        # 1. MTF FVG Detection (Adapted to 30m data)
        # Bull FVG: low > high[2]
        if l > highs[i-2]:
            act_bull_fvg_bot = highs[i-2]
            act_bull_fvg_top = l
        if h < lows[i-2]:
            act_bear_fvg_top = lows[i-2]
            act_bear_fvg_bot = h
            
        # Mitigation
        if not np.isnan(act_bull_fvg_bot) and c < act_bull_fvg_bot:
            act_bull_fvg_bot = np.nan
            act_bull_fvg_top = np.nan
        if not np.isnan(act_bear_fvg_top) and c > act_bear_fvg_top:
            act_bear_fvg_top = np.nan
            act_bear_fvg_bot = np.nan
            
        # 2. Pivot Tracking
        ph = np.nan
        pl = np.nan
        if highs[i-1] > highs[i-2] and highs[i-1] > highs[i-3] and highs[i-1] > h:
            ph = highs[i-1]
        if lows[i-1] < lows[i-2] and lows[i-1] < lows[i-3] and lows[i-1] < l:
            pl = lows[i-1]
            
        if not np.isnan(ph):
            last_ph = ph
        if not np.isnan(pl):
            last_pl = pl
            
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
        
        # 3. Setup Locking
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
            
        if act_long_setup and h > lock_swing_high:
            lock_swing_high = h
        if act_short_setup and l < lock_swing_low:
            lock_swing_low = l
            
        if act_long_setup and c < lock_swing_low:
            act_long_setup = False
        if act_short_setup and c > lock_swing_high:
            act_short_setup = False
            
        # Track Local FVGs
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
            
        # Cancel Limits
        if not act_long_setup and limit_type == 1:
            limit_type = 0
        if not act_short_setup and limit_type == -1:
            limit_type = 0
            
        # Define Orders
        if position == 0:
            if act_long_setup:
                fib_lvl = lock_swing_high - in_fib_lvl * (lock_swing_high - lock_swing_low)
                fib_786 = lock_swing_high - 0.786 * (lock_swing_high - lock_swing_low)
                
                fvg_in_zone = not np.isnan(act_bull_1m_fvg_top) and act_bull_1m_fvg_top <= fib_lvl and act_bull_1m_fvg_bot >= fib_786
                if fvg_in_zone:
                    limit_entry_price = (act_bull_1m_fvg_top + act_bull_1m_fvg_bot) / 2
                    initial_sl_price = lock_swing_low - (atrs[i] * 0.5)
                    risk = limit_entry_price - initial_sl_price
                    if risk > 0:
                        tp_2r_price = limit_entry_price + (risk * in_tp1_r)
                        current_tp_price = limit_entry_price + (risk * in_tp2_r)
                        if use_fixed_margin:
                            position_value = capital * (in_margin_pct * leverage)
                            limit_qty = position_value / limit_entry_price
                        else:
                            limit_qty = (capital * in_risk_pct) / risk
                        limit_type = 1
                        
            if act_short_setup:
                fib_lvl = lock_swing_low + in_fib_lvl * (lock_swing_high - lock_swing_low)
                fib_786 = lock_swing_low + 0.786 * (lock_swing_high - lock_swing_low)
                
                fvg_in_zone = not np.isnan(act_bear_1m_fvg_top) and act_bear_1m_fvg_bot >= fib_lvl and act_bear_1m_fvg_top <= fib_786
                if fvg_in_zone:
                    limit_entry_price = (act_bear_1m_fvg_top + act_bear_1m_fvg_bot) / 2
                    initial_sl_price = lock_swing_high + (atrs[i] * 0.5)
                    risk = initial_sl_price - limit_entry_price
                    if risk > 0:
                        tp_2r_price = limit_entry_price - (risk * in_tp1_r)
                        current_tp_price = limit_entry_price - (risk * in_tp2_r)
                        if use_fixed_margin:
                            position_value = capital * (in_margin_pct * leverage)
                            limit_qty = position_value / limit_entry_price
                        else:
                            limit_qty = (capital * in_risk_pct) / risk
                        limit_type = -1
                        
            # Execute Limits
            if limit_type == 1 and l <= limit_entry_price and h >= limit_entry_price:
                position = 1
                entry_price = limit_entry_price + (tick_size * 2) # Slippage on entry
                entry_time = str(df.index[i])
                qty = limit_qty
                sl = initial_sl_price
                tp1 = tp_2r_price
                tp2 = current_tp_price
                tp1_done = False
                limit_type = 0
            elif limit_type == -1 and h >= limit_entry_price and l <= limit_entry_price:
                position = -1
                entry_price = limit_entry_price - (tick_size * 2)
                entry_time = str(df.index[i])
                qty = limit_qty
                sl = initial_sl_price
                tp1 = tp_2r_price
                tp2 = current_tp_price
                tp1_done = False
                limit_type = 0

        # Position Management
        if position != 0:
            if position == 1:
                if c > lock_swing_high:
                    sl = entry_price # BE
                    
                hit_sl = l <= sl
                hit_tp1 = h >= tp1 and not tp1_done
                hit_tp2 = h >= tp2
                
                if hit_sl and not (hit_tp1 or hit_tp2):
                    pnl = (sl - entry_price) * qty - (entry_price * qty * 0.0005) - (sl * qty * 0.0005) # 0.05% comm
                    capital += pnl
                    trades.append({'time': df.index[i], 'type': 'SL_L', 'pnl': pnl, 'entry_time': entry_time, 'entry_price': entry_price, 'exit_price': sl})
                    position = 0
                elif hit_sl and (hit_tp1 or hit_tp2):
                    pnl = (sl - entry_price) * qty - (entry_price * qty * 0.0005) - (sl * qty * 0.0005)
                    capital += pnl
                    trades.append({'time': df.index[i], 'type': 'SL_L_Vol', 'pnl': pnl, 'entry_time': entry_time, 'entry_price': entry_price, 'exit_price': sl})
                    position = 0
                else:
                    if hit_tp1:
                        pnl = (tp1 - entry_price) * (qty * 0.5) - (entry_price * qty * 0.5 * 0.0005) - (tp1 * qty * 0.5 * 0.0005)
                        capital += pnl
                        trades.append({'time': df.index[i], 'type': 'TP1_L', 'pnl': pnl, 'entry_time': entry_time, 'entry_price': entry_price, 'exit_price': tp1})
                        qty = qty * 0.5
                        tp1_done = True
                    if hit_tp2:
                        pnl = (tp2 - entry_price) * qty - (entry_price * qty * 0.0005) - (tp2 * qty * 0.0005)
                        capital += pnl
                        trades.append({'time': df.index[i], 'type': 'TP2_L', 'pnl': pnl, 'entry_time': entry_time, 'entry_price': entry_price, 'exit_price': tp2})
                        position = 0

            elif position == -1:
                if c < lock_swing_low:
                    sl = entry_price # BE
                    
                hit_sl = h >= sl
                hit_tp1 = l <= tp1 and not tp1_done
                hit_tp2 = l <= tp2
                
                if hit_sl and not (hit_tp1 or hit_tp2):
                    pnl = (entry_price - sl) * qty - (entry_price * qty * 0.0005) - (sl * qty * 0.0005)
                    capital += pnl
                    trades.append({'time': df.index[i], 'type': 'SL_S', 'pnl': pnl, 'entry_time': entry_time, 'entry_price': entry_price, 'exit_price': sl})
                    position = 0
                elif hit_sl and (hit_tp1 or hit_tp2):
                    pnl = (entry_price - sl) * qty - (entry_price * qty * 0.0005) - (sl * qty * 0.0005)
                    capital += pnl
                    trades.append({'time': df.index[i], 'type': 'SL_S_Vol', 'pnl': pnl, 'entry_time': entry_time, 'entry_price': entry_price, 'exit_price': sl})
                    position = 0
                else:
                    if hit_tp1:
                        pnl = (entry_price - tp1) * (qty * 0.5) - (entry_price * qty * 0.5 * 0.0005) - (tp1 * qty * 0.5 * 0.0005)
                        capital += pnl
                        trades.append({'time': df.index[i], 'type': 'TP1_S', 'pnl': pnl, 'entry_time': entry_time, 'entry_price': entry_price, 'exit_price': tp1})
                        qty = qty * 0.5
                        tp1_done = True
                    if hit_tp2:
                        pnl = (entry_price - tp2) * qty - (entry_price * qty * 0.0005) - (tp2 * qty * 0.0005)
                        capital += pnl
                        trades.append({'time': df.index[i], 'type': 'TP2_S', 'pnl': pnl, 'entry_time': entry_time, 'entry_price': entry_price, 'exit_price': tp2})
                        position = 0

        equity_curve.append({'time': df.index[i], 'equity': capital})
        
    return trades, equity_curve

def generate_report(symbol, trades, equity_curve):
    if not trades:
        return f"### Backtest Results (Last 6 Months): {symbol}\nNo trades executed.\n"
        
    df_trades = pd.DataFrame(trades)
    df_eq = pd.DataFrame(equity_curve)
    
    initial_capital = 10000.0
    final_equity = df_eq['equity'].iloc[-1]
    
    # Calculate percentages
    total_return_pct = ((final_equity - initial_capital) / initial_capital) * 100
    
    df_eq['high_water_mark'] = df_eq['equity'].cummax()
    df_eq['drawdown_pct'] = ((df_eq['equity'] - df_eq['high_water_mark']) / df_eq['high_water_mark']) * 100
    max_dd_pct = df_eq['drawdown_pct'].min()
    
    profitable_trades = len(df_trades[df_trades['pnl'] > 0])
    total_trades = len(df_trades)
    win_rate = (profitable_trades / total_trades) * 100 if total_trades > 0 else 0
    
    gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
    gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
    
    df_eq.set_index('time', inplace=True)
    # Resample to monthly and compute percent change
    monthly_equity = df_eq['equity'].resample('ME').last()
    
    report = f"### Backtest Results (Last 6 Months): {symbol}\n"
    report += f"- **Total Return:** {total_return_pct:.2f}%\n"
    report += f"- **Max Drawdown:** {max_dd_pct:.2f}%\n"
    report += f"- **Profit Factor:** {profit_factor:.2f}\n"
    report += f"- **Total Trades:** {total_trades}\n"
    report += f"- **Profitable Trades:** {profitable_trades} ({win_rate:.1f}%)\n"
    
    report += "\n#### Month by Month Return:\n"
    prev_eq = initial_capital
    for idx, eq in monthly_equity.items():
        if pd.isna(eq): continue
        m_return = ((eq - prev_eq) / prev_eq) * 100
        report += f"- {idx.strftime('%Y-%B')}: {m_return:.2f}%\n"
        prev_eq = eq
        
    return report

def main():
    import os
    report_all = ""
    symbols_to_run = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'PEPEUSDT', 'AVAUSDT', 'DOGEUSDT', 'LTCUSDT']
    
    for symbol in symbols_to_run:
        print(f"Running SMC backtest for {symbol}...")
        
        # Determine correct file path
        if os.path.exists(f"data/{symbol}_30m_365d.csv"):
            file_path = f"data/{symbol}_30m_365d.csv"
        elif os.path.exists(f"data/{symbol}_30m_1y.csv"):
            file_path = f"data/{symbol}_30m_1y.csv"
        else:
            print(f"Data file for {symbol} not found! Skipping.")
            continue
            
        df = pd.read_csv(file_path, index_col='timestamp', parse_dates=True)
        
        # Filter for the last 6 months (180 days)
        cutoff_date = df.index[-1] - pd.Timedelta(days=180)
        df = df[df.index >= cutoff_date]
        
        # Calculate tick size dynamically based on min price movement
        tick = df['close'].diff().abs().replace(0, np.nan).min()
        if pd.isna(tick):
            tick = 0.01 # fallback
            
        df = compute_indicators(df)
        
        trades, equity_curve = smc_backtest(df, tick_size=tick)
        report = generate_report(symbol, trades, equity_curve)
        report_all += report + "\n\n"
        
    with open('data/smc_results.md', 'w') as f:
        f.write(report_all)
        
    print("SMC Backtest complete!")

if __name__ == '__main__':
    main()

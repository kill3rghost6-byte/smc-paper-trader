import pandas as pd
import numpy as np
import os
from smc_backtester import smc_backtest, compute_indicators

def get_trades(symbol, timeframe):
    # Try different data files
    file_path = f"data/{symbol}_{timeframe}_365d.csv"
    if not os.path.exists(file_path):
        file_path = f"data/{symbol}_{timeframe}_1y.csv"
    if not os.path.exists(file_path):
        return []
        
    df = pd.read_csv(file_path, index_col='timestamp', parse_dates=True)
    
    cutoff_date = df.index[-1] - pd.Timedelta(days=365)
    df = df[df.index >= cutoff_date]
    
    compute_indicators(df)
    tick = df['close'].diff().abs().replace(0, np.nan).min()
    if pd.isna(tick): tick = 0.01
    
    trades, _ = smc_backtest(df, tick_size=tick, leverage=1)
    
    # Calculate R-multiple assuming 1% risk initially
    for t in trades:
        t['r_multiple'] = t['pnl'] / 100.0
        t['symbol'] = f"{symbol}_{timeframe}"
    return trades

def simulate_portfolio(all_trades, weights, initial_capital=10000):
    sorted_trades = sorted(all_trades, key=lambda x: x['time'])
    
    equity = initial_capital
    peak_equity = initial_capital
    max_drawdown_pct = 0.0
    equity_curve = []
    
    for t in sorted_trades:
        symbol = t['symbol']
        if weights.get(symbol, 0) == 0:
            continue
            
        risk_pct = weights[symbol]
        trade_pnl = equity * risk_pct * t['r_multiple']
        equity += trade_pnl
        
        if equity > peak_equity:
            peak_equity = equity
            
        drawdown = (peak_equity - equity) / peak_equity
        if drawdown > max_drawdown_pct:
            max_drawdown_pct = drawdown
            
        equity_curve.append({'time': t['time'], 'equity': equity})
        
        if equity <= 0:
            equity = 0
            break
            
    return equity, max_drawdown_pct, equity_curve

if __name__ == '__main__':
    # Default SMC Portfolio Weights
    WEIGHTS_SMC = {
        'BTCUSDT_30m': 0.0279,
        'DOGEUSDT_15m': 0.0230,
        'XRPUSDT_15m': 0.0238
    }

    print("Fetching trades for SMC strategies...")
    all_trades = []
    for k in WEIGHTS_SMC.keys():
        sym, tf = k.split('_')
        tr = get_trades(sym, tf)
        all_trades.extend(tr)
        
    print(f"Total historical SMC trades found: {len(all_trades)}")
    
    final_eq, mdd, curve = simulate_portfolio(all_trades, WEIGHTS_SMC)
    
    print("\n" + "="*40)
    print("📊 SMC PORTFOLIO CHRONOLOGICAL BACKTEST")
    print("="*40)
    print(f"Initial Capital: $10,000.00")
    print(f"Final Capital:   ${final_eq:,.2f}")
    
    roi = ((final_eq - 10000) / 10000) * 100
    print(f"Net Profit:      {roi:+.2f}%")
    print(f"Max Drawdown:    {mdd*100:.2f}%")
    
    if curve:
        df_eq = pd.DataFrame(curve)
        df_eq.set_index('time', inplace=True)
        monthly = df_eq['equity'].resample('ME').last()
        
        print("\n📅 Month-by-Month Performance:")
        prev = 10000
        for m, val in monthly.items():
            if pd.isna(val): continue
            pct = ((val - prev) / prev) * 100
            print(f"   {m.strftime('%Y-%b')}: {pct:+.2f}%")
            prev = val

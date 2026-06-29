import pandas as pd
import numpy as np
import os
import random
from smc_backtester import smc_backtest, compute_indicators

def get_trades(symbol, timeframe):
    file_path = f"data/{symbol}_{timeframe}_365d.csv"
    if not os.path.exists(file_path):
        return []
    df = pd.read_csv(file_path, index_col='timestamp', parse_dates=True)
    compute_indicators(df)
    tick = df['close'].diff().abs().replace(0, np.nan).min()
    if pd.isna(tick): tick = 0.01
    
    # We use leverage=1 to get the base trades.
    trades, _ = smc_backtest(df, tick_size=tick, leverage=1)
    # We need to compute the R-multiple for each trade. 
    # Since the default risk is 1% (in_risk_pct = 0.01) on 10000 capital, 1R = 100 USD.
    for t in trades:
        t['r_multiple'] = t['pnl'] / 100.0
        t['symbol'] = f"{symbol}_{timeframe}"
    return trades

def simulate_portfolio(all_trades, weights, initial_capital=10000):
    # weights is a dict mapping symbol to risk percentage (e.g. 0.01 for 1% risk)
    # Process trades chronologically by time
    sorted_trades = sorted(all_trades, key=lambda x: x['time'])
    
    equity = initial_capital
    peak_equity = initial_capital
    max_drawdown_pct = 0.0
    
    for t in sorted_trades:
        symbol = t['symbol']
        if weights.get(symbol, 0) == 0:
            continue
            
        risk_pct = weights[symbol]
        # Trade PnL = Equity * Risk % * R_multiple
        trade_pnl = equity * risk_pct * t['r_multiple']
        equity += trade_pnl
        
        if equity > peak_equity:
            peak_equity = equity
        
        drawdown = (peak_equity - equity) / peak_equity
        if drawdown > max_drawdown_pct:
            max_drawdown_pct = drawdown
            
        if equity <= 0:
            equity = 0
            break
            
    return equity, max_drawdown_pct

def main():
    tasks = [
        ('BTCUSDT', '30m'), ('AVAXUSDT', '15m'), ('TONUSDT', '3m'), 
        ('DOGEUSDT', '15m'), ('TRXUSDT', '30m'), ('LTCUSDT', '3m'),
        ('ARBUSDT', '3m'), ('AAVEUSDT', '3m'), ('HBARUSDT', '5m')
    ]
    
    print("Extracting trades for all strategies...")
    all_trades = []
    symbol_keys = []
    for sym, tf in tasks:
        trades = get_trades(sym, tf)
        all_trades.extend(trades)
        symbol_keys.append(f"{sym}_{tf}")
        
    print(f"Total trades across all strategies: {len(all_trades)}")
    
    print("Running Monte Carlo simulation (10,000 iterations)...")
    best_portfolios = []
    
    for i in range(10000):
        # We want to find combinations that yield high return with low drawdown.
        # Randomly assign a risk between 0.0% and 5.0% for each strategy
        # A 0% means the strategy is excluded.
        weights = {}
        for k in symbol_keys:
            # 50% chance to include this strategy
            if random.random() > 0.5:
                weights[k] = random.uniform(0.005, 0.03) # 0.5% to 3% risk per trade
            else:
                weights[k] = 0.0
                
        # To avoid unrealistic total risk, ensure total risk per trade doesn't exceed 10%
        # (Though they don't always happen concurrently)
        if sum(weights.values()) > 0.15:
            continue
            
        final_eq, mdd = simulate_portfolio(all_trades, weights)
        
        total_return = ((final_eq - 10000) / 10000)
        
        # Target: roughly 10% per month = 120% per year => total_return > 1.2
        if total_return > 1.2 and mdd < 0.30: # Max 30% drawdown
            best_portfolios.append({
                'return': total_return * 100,
                'mdd': mdd * 100,
                'weights': weights
            })
            
    best_portfolios.sort(key=lambda x: x['return'] / (x['mdd'] + 1e-5), reverse=True)
    
    print("\n=== TOP 5 MONTE CARLO PORTFOLIOS (Target: >120% Annual Return, Low Drawdown) ===")
    for i, p in enumerate(best_portfolios[:5], 1):
        print(f"\nPortfolio {i}:")
        print(f"Total Annual Return: {p['return']:.2f}% (Average ~{p['return']/12:.2f}% per month)")
        print(f"Max Drawdown: {p['mdd']:.2f}%")
        print("Strategy Allocation (Risk % per trade):")
        for k, v in p['weights'].items():
            if v > 0:
                print(f"  - {k}: {v*100:.2f}% risk")

if __name__ == '__main__':
    main()

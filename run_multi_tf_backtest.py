import pandas as pd
import numpy as np
import os
from smc_backtester import smc_backtest, generate_report, compute_indicators

def main():
    report_all = "# Multi-Timeframe SMC Backtest Results (5x Leverage, 1 Year Data)\n\n"
    
    tasks = [
        ('BTCUSDT', '30m'),
        ('AVAXUSDT', '15m'),
        ('TONUSDT', '3m'),
        ('DOGEUSDT', '15m'),
        ('TRXUSDT', '30m'),
        ('LTCUSDT', '3m'),
        ('ARBUSDT', '3m'),
        ('AAVEUSDT', '3m'),
        ('HBARUSDT', '5m')
    ]
    
    results = []
    
    for symbol, timeframe in tasks:
        file_path = f"data/{symbol}_{timeframe}_365d.csv"
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue
            
        print(f"Running backtest for {symbol} ({timeframe})...")
        df = pd.read_csv(file_path, index_col='timestamp', parse_dates=True)
        
        # Compute EMA and ATR
        compute_indicators(df)
        
        tick = df['close'].diff().abs().replace(0, np.nan).min()
        if pd.isna(tick):
            tick = 0.01
            
        # Run with 5x leverage
        trades, equity_curve = smc_backtest(df, tick_size=tick, leverage=5)
        
        initial_capital = 10000.0
        final_equity = equity_curve[-1]['equity'] if equity_curve else initial_capital
        total_return_pct = ((final_equity - initial_capital) / initial_capital) * 100
        
        win_rate = 0
        if trades:
            wins = sum(1 for t in trades if t['pnl'] > 0)
            win_rate = (wins / len(trades)) * 100
            
        results.append({
            'symbol': symbol,
            'timeframe': timeframe,
            'return': total_return_pct,
            'win_rate': win_rate,
            'trades_count': len(trades),
            'equity_curve': equity_curve,
            'trades': trades,
            'df': df
        })
        
    # Sort results by return descending
    results.sort(key=lambda x: x['return'], reverse=True)
    
    report_all += "## 🏆 Performance Ranking (Best to Worst)\n\n"
    for rank, res in enumerate(results, 1):
        report_all += f"{rank}. **{res['symbol']} ({res['timeframe']})**: {res['return']:.2f}% Return (Win Rate: {res['win_rate']:.1f}%, Trades: {res['trades_count']})\n"
        
    report_all += "\n---\n\n"
    
    for res in results:
        symbol = res['symbol']
        timeframe = res['timeframe']
        trades = res['trades']
        equity_curve = res['equity_curve']
        df = res['df']
        
        report_all += f"## {symbol} ({timeframe})\n"
        report_all += f"- **Period**: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')} ({(df.index[-1] - df.index[0]).days} days)\n"
        report_all += generate_report(f"{symbol} ({timeframe})", trades, equity_curve)
        
    with open("data/multi_tf_results_5x.md", "w") as f:
        f.write(report_all)
        
    print("Backtest completed. Results saved to data/multi_tf_results_5x.md")

if __name__ == "__main__":
    main()

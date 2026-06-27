import pandas as pd
import numpy as np
import os
from smc_backtester import smc_backtest, generate_report, compute_indicators

def main():
    report_all = "# SMC Strategy Backtest Results on Toobit (30m Timeframe)\n\n"
    report_all += "Note: Toobit API restricts historical public data on 30m chart to roughly the last ~73 days (3,500 candles).\n\n"
    
    symbols_to_run = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'PEPEUSDT', 'AVAUSDT', 'DOGEUSDT', 'LTCUSDT']
    
    for symbol in symbols_to_run:
        print(f"Running SMC backtest for {symbol} on Toobit data...")
        
        file_path = f"data/toobit_{symbol}_30m_180d.csv"
        
        if not os.path.exists(file_path):
            print(f"Data file for {symbol} not found! Skipping.")
            continue
            
        df = pd.read_csv(file_path, index_col='timestamp', parse_dates=True)
        
        # Compute EMA and ATR
        compute_indicators(df)
        
        # Calculate tick size dynamically based on min price movement
        tick = df['close'].diff().abs().replace(0, np.nan).min()
        if pd.isna(tick):
            tick = 0.01  # fallback
            
        print(f"[{symbol}] Dynamically calculated tick size: {tick}")
        
        trades, equity_curve = smc_backtest(df, tick_size=tick)
        
        initial_capital = 10000.0
        final_equity = equity_curve[-1]['equity'] if equity_curve else initial_capital
        
        report_all += f"## {symbol}\n"
        report_all += f"- **Period**: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')} ({(df.index[-1] - df.index[0]).days} days)\n"
        report_all += f"- **Total Candles**: {len(df)}\n"
        report_all += generate_report(symbol, trades, equity_curve)
        
    with open("data/toobit_smc_results.md", "w") as f:
        f.write(report_all)
        
    print("Done! Results saved to data/toobit_smc_results.md")

if __name__ == "__main__":
    main()

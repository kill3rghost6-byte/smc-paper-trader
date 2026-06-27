import pandas as pd
from backtester import compute_indicators, backtest_strategy

def generate_report(symbol, trades, equity_curve):
    if not trades:
        return f"No trades executed for {symbol}."
        
    df_trades = pd.DataFrame(trades)
    df_eq = pd.DataFrame(equity_curve)
    
    total_pnl = df_trades['pnl'].sum()
    profitable_trades = len(df_trades[df_trades['pnl'] > 0])
    total_trades = len(df_trades)
    win_rate = (profitable_trades / total_trades) * 100 if total_trades > 0 else 0
    
    gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
    gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
    
    # Max DD
    df_eq['high_water_mark'] = df_eq['equity'].cummax()
    df_eq['drawdown'] = df_eq['equity'] - df_eq['high_water_mark']
    max_dd = df_eq['drawdown'].min()
    
    # Month by Month P&L
    df_eq.set_index('time', inplace=True)
    df_monthly = df_eq['equity'].resample('ME').last().diff().fillna(df_eq['equity'].iloc[0] - 10000)
    
    report = f"### Backtest Results: {symbol}\n"
    report += f"- **Total P&L:** ${total_pnl:.2f}\n"
    report += f"- **Max Drawdown:** ${max_dd:.2f}\n"
    report += f"- **Profit Factor:** {profit_factor:.2f}\n"
    report += f"- **Total Trades:** {total_trades}\n"
    report += f"- **Profitable Trades:** {profitable_trades} ({win_rate:.1f}%)\n"
    
    report += "\n#### Month by Month P&L:\n"
    for idx, val in df_monthly.items():
        report += f"- {idx.strftime('%Y-%B')}: ${val:.2f}\n"
        
    return report

def main():
    report_all = ""
    for symbol, tick in [('BTCUSDT', 0.1), ('ETHUSDT', 0.01)]:
        print(f"Running backtest for {symbol}...")
        df = pd.read_csv(f"data/{symbol}_30m_1y.csv", index_col='timestamp', parse_dates=True)
        df = compute_indicators(df)
        
        trades, equity_curve = backtest_strategy(df, tick_size=tick)
        report = generate_report(symbol, trades, equity_curve)
        report_all += report + "\n\n"
        
    with open('data/backtest_results.md', 'w') as f:
        f.write(report_all)
        
    print("Backtest complete!")

if __name__ == '__main__':
    main()

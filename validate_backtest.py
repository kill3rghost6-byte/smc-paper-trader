import pandas as pd
import numpy as np
import json
from monte_carlo_portfolio import get_trades

def run_validation():
    print("Validating Trades...")
    
    # Portfolio 1 Weights
    weights = {
        'BTCUSDT_30m': 0.0281,
        'TRXUSDT_30m': 0.0230,
        'DOGEUSDT_15m': 0.0181
    }
    
    all_trades = []
    for sym in weights.keys():
        s, tf = sym.split('_')
        trades = get_trades(s, tf)
        # Add risk-adjusted PnL for individual tracking
        for t in trades:
            t['risk_pct'] = weights[sym]
        all_trades.extend(trades)
        
    sorted_trades = sorted(all_trades, key=lambda x: x['time'])
    
    # Simulate Combined Portfolio
    capital = 10000
    monthly_data = {}
    
    for t in sorted_trades:
        # PnL = Capital * risk_pct * r_multiple
        pnl = capital * t['risk_pct'] * t['r_multiple']
        capital += pnl
        
        # Group by month
        month = t['time'].strftime('%Y-%m')
        if month not in monthly_data:
            monthly_data[month] = {
                'total_trades': 0,
                'wins': 0,
                'pnl_usd': 0.0,
                'BTCUSDT_30m_pnl': 0.0,
                'TRXUSDT_30m_pnl': 0.0,
                'DOGEUSDT_15m_pnl': 0.0
            }
            
        md = monthly_data[month]
        md['total_trades'] += 1
        if t['r_multiple'] > 0:
            md['wins'] += 1
        md['pnl_usd'] += pnl
        md[f"{t['symbol']}_pnl"] += pnl
        
    print(f"Final Capital: ${capital:.2f}")
    
    # Format Output
    output = []
    for m in sorted(monthly_data.keys()):
        d = monthly_data[m]
        output.append({
            'month': m,
            'trades': d['total_trades'],
            'win_rate': (d['wins'] / d['total_trades'] * 100) if d['total_trades'] > 0 else 0,
            'profit': d['pnl_usd'],
            'btc': d['BTCUSDT_30m_pnl'],
            'trx': d['TRXUSDT_30m_pnl'],
            'doge': d['DOGEUSDT_15m_pnl']
        })
        
    with open('validation_results.json', 'w') as f:
        json.dump({'final_capital': capital, 'monthly': output}, f, indent=4)
        
    print("Validation Complete. Results written to validation_results.json")

if __name__ == '__main__':
    run_validation()

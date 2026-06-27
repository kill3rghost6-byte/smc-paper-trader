import json
from monte_carlo_portfolio import get_trades

def run_validation():
    print("Validating Trades for Top 5 Portfolios...")
    
    portfolios = [
        {
            "name": "پورتفولیو ۱ (امن) 🏆",
            "weights": {'BTCUSDT_30m': 0.0281, 'TRXUSDT_30m': 0.0230, 'DOGEUSDT_15m': 0.0181}
        },
        {
            "name": "پورتفولیو ۲ (هجومی) 🚀",
            "weights": {'BTCUSDT_30m': 0.0279, 'DOGEUSDT_15m': 0.0230, 'TRXUSDT_30m': 0.0195}
        },
        {
            "name": "پورتفولیو ۳ (پرنوسان) 🔥",
            "weights": {'BTCUSDT_30m': 0.0259, 'TRXUSDT_30m': 0.0278, 'DOGEUSDT_15m': 0.0223}
        },
        {
            "name": "پورتفولیو ۴ (فوق ایمن) 🛡️",
            "weights": {'TRXUSDT_30m': 0.0243, 'BTCUSDT_30m': 0.0214, 'DOGEUSDT_15m': 0.0145}
        },
        {
            "name": "پورتفولیو ۵ (تعادل) ⚡",
            "weights": {'TRXUSDT_30m': 0.0286, 'DOGEUSDT_15m': 0.0247, 'BTCUSDT_30m': 0.0215}
        }
    ]
    
    # Load all unique trades first to save time
    unique_symbols = set()
    for p in portfolios:
        for s in p['weights'].keys():
            unique_symbols.add(s)
            
    loaded_trades = {}
    for sym in unique_symbols:
        s, tf = sym.split('_')
        loaded_trades[sym] = get_trades(s, tf)

    results = []
    
    for idx, p in enumerate(portfolios):
        all_trades = []
        for sym, weight in p['weights'].items():
            for t in loaded_trades[sym]:
                # Make a copy of the trade to add risk_pct
                t_copy = t.copy()
                t_copy['risk_pct'] = weight
                all_trades.append(t_copy)
                
        sorted_trades = sorted(all_trades, key=lambda x: x['time'])
        
        capital = 10000
        peak = 10000
        mdd = 0
        monthly_data = {}
        eq_curve = [10000]
        
        for t in sorted_trades:
            pnl = capital * t['risk_pct'] * t['r_multiple']
            capital += pnl
            eq_curve.append(capital)
            
            if capital > peak: peak = capital
            dd = (peak - capital) / peak
            if dd > mdd: mdd = dd
            
            month = t['time'].strftime('%Y-%m')
            if month not in monthly_data:
                monthly_data[month] = {
                    'total_trades': 0, 'wins': 0, 'pnl_usd': 0.0,
                    'coins': {k: {'pnl': 0.0, 'trades': []} for k in p['weights'].keys()}
                }
                
            md = monthly_data[month]
            md['total_trades'] += 1
            if t['r_multiple'] > 0: md['wins'] += 1
            md['pnl_usd'] += pnl
            
            # Format trade for frontend
            trade_obj = {
                'entry_time': t.get('entry_time', ''),
                'exit_time': t['time'].strftime('%Y-%m-%d %H:%M') if hasattr(t['time'], 'strftime') else str(t['time']),
                'type': t['type'],
                'order_type': 'Limit',
                'entry_price': t.get('entry_price', 0),
                'exit_price': t.get('exit_price', 0),
                'pnl': pnl
            }
            md['coins'][t['symbol']]['pnl'] += pnl
            md['coins'][t['symbol']]['trades'].append(trade_obj)

        month_arr = []
        for m in sorted(monthly_data.keys()):
            d = monthly_data[m]
            month_arr.append({
                'month': m,
                'profit': d['pnl_usd'],
                'trades': d['total_trades'],
                'coins': d['coins']
            })
            
        ret = ((capital - 10000) / 10000) * 100
        results.append({
            'name': p['name'],
            'weights': p['weights'],
            'return': ret,
            'mdd': mdd * 100,
            'monthly_avg': ret / 12,
            'eq_curve': eq_curve[::max(1, len(eq_curve)//50)], # downsample for chart
            'logs': month_arr
        })
        
    with open('all_portfolios_validation.json', 'w') as f:
        json.dump(results, f, indent=4)
        
    print("Validation Complete. Check all_portfolios_validation.json")

if __name__ == '__main__':
    run_validation()

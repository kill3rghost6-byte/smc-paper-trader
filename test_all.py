import smc_live_bot
symbols_tf = {'BTCUSDT': '30m', 'DOGEUSDT': '15m', 'TRXUSDT': '30m'}
for symbol, tf in symbols_tf.items():
    df = smc_live_bot.fetch_data(symbol, tf)
    df = smc_live_bot.compute_indicators(df)
    tick = df['close'].diff().abs().replace(0, float('nan')).min()
    state = smc_live_bot.get_live_state(df, tick, symbol)
    for t in state['completed_trades']:
        if str(t['exit_time']) >= '2026-06-29 17:24':
            print(f"  {t['symbol']} | {t['direction']} | {t['entry_time']} -> {t['exit_time']} | R: {t['r_multiple']}")

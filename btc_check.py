import pandas as pd
import smc_live_bot as bot

df = bot.fetch_data('BTCUSDT', '30m', limit=100)
print(f"BTC Current Price (Close of latest 30m candle): {df.iloc[-1]['close']}")
print(f"BTC Lowest Price in last 48h: {df['low'].min()}")

df = bot.compute_indicators(df)
state = bot.get_live_state(df, 0.1, 'BTCUSDT')
print("BTC State from get_live_state:")
print(f"  Position: {state['position']}")
print(f"  Limit Type: {state['limit_type']}")
print(f"  Entry Price / Limit Price: {state['entry_price']}")

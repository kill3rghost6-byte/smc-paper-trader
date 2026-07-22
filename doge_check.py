import pandas as pd
import smc_live_bot as bot

df = bot.fetch_data('DOGEUSDT', '15m', limit=200)
df = bot.compute_indicators(df)

limit_entry = 0.07716
sl = 0.07756
tp2 = 0.07554

print("DOGEUSDT 15m Price Action (Last 24h):")
df_sub = df[df.index >= pd.Timestamp('2026-07-04 12:00:00')]

for ts, row in df_sub.iterrows():
    h = row['high']
    l = row['low']
    c = row['close']
    
    # Check if entry was hit
    if h >= limit_entry and l <= limit_entry:
        print(f"[{ts}] ENTRY {limit_entry} HIT! (High: {h}, Low: {l})")
    elif l > limit_entry:
        print(f"[{ts}] GAP THROUGH ENTRY {limit_entry} (Low: {l})")
        
    # Check if TP2 was hit
    if l <= tp2:
        print(f"[{ts}] TP2 {tp2} HIT! (Low: {l})")
        
    # Check if SL (Swing High) broken on close
    if c > sl:
        print(f"[{ts}] CLOSE ABOVE SL {sl} (Close: {c}) -> SETUP INVALIDATED")
        
    # Check if SL was hit
    if h >= sl:
        print(f"[{ts}] SL {sl} HIT! (High: {h})")


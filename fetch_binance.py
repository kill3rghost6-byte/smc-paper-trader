import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import os

class BinanceDataFetcher:
    def __init__(self):
        self.timeframes = ['1h', '1d', '4h', '1w', '30m']
        self.binance_base_url = 'https://api.binance.com/api/v3/klines'
    
    def fetch_data(self, symbol, interval, start_time_ms, end_time_ms):
        all_klines = []
        current_start = start_time_ms
        
        while current_start < end_time_ms:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': current_start,
                'endTime': end_time_ms,
                'limit': 1000
            }
            try:
                response = requests.get(self.binance_base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    break
                    
                all_klines.extend(data)
                current_start = data[-1][0] + 1
                time.sleep(0.5) # rate limit prevention
                
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                if response:
                    print(f"Response: {response.text}")
                break
                
        return all_klines

fetcher = BinanceDataFetcher()
end_time = datetime.now()
start_time = end_time - timedelta(days=365)

end_ms = int(end_time.timestamp() * 1000)
start_ms = int(start_time.timestamp() * 1000)

os.makedirs('data', exist_ok=True)

for symbol in ['BTCUSDT', 'ETHUSDT']:
    print(f"Fetching {symbol} 30m data for 1 year...")
    klines = fetcher.fetch_data(symbol, '30m', start_ms, end_ms)
    if klines:
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
            
        df = df[['open', 'high', 'low', 'close', 'volume']]
        file_path = f"data/{symbol}_30m_1y.csv"
        df.to_csv(file_path)
        print(f"Saved {symbol} data to {file_path}. Rows: {len(df)}")

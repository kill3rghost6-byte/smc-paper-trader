import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import os

# ==============================================================================
# تنظمیات دانلود (مکان‌هایی که شما باید تغییر دهید)
# ==============================================================================

TASKS = [
    {'symbol': 'BTCUSDT', 'timeframe': '30m'},
    {'symbol': 'AVAXUSDT', 'timeframe': '15m'},
    {'symbol': 'TONUSDT', 'timeframe': '3m'},
    {'symbol': 'DOGEUSDT', 'timeframe': '15m'},
    {'symbol': 'TRXUSDT', 'timeframe': '30m'},
    {'symbol': 'LTCUSDT', 'timeframe': '3m'},
    {'symbol': 'ARBUSDT', 'timeframe': '3m'},
    {'symbol': 'AAVEUSDT', 'timeframe': '3m'},
    {'symbol': 'HBARUSDT', 'timeframe': '5m'} # Corrected HBRUSDT to HBARUSDT (Binance standard)
]
DAYS_TO_DOWNLOAD = 365

# ==============================================================================
# کد اصلی (نیاز به تغییر ندارد)
# ==============================================================================

class BinanceDataFetcher:
    def __init__(self):
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
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                response = requests.get(self.binance_base_url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    break
                    
                all_klines.extend(data)
                current_start = data[-1][0] + 1
                time.sleep(0.2) # rate limit prevention
                
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                if 'response' in locals():
                    print(f"Response: {response.text}")
                break
                
        return all_klines

if __name__ == '__main__':
    fetcher = BinanceDataFetcher()
    end_time = datetime.now()
    start_time = end_time - timedelta(days=DAYS_TO_DOWNLOAD)

    end_ms = int(end_time.timestamp() * 1000)
    start_ms = int(start_time.timestamp() * 1000)

    os.makedirs('data', exist_ok=True)

    for task in TASKS:
        symbol = task['symbol']
        timeframe = task['timeframe']
        print(f"Fetching {symbol} {timeframe} data for {DAYS_TO_DOWNLOAD} days...")
        klines = fetcher.fetch_data(symbol, timeframe, start_ms, end_ms)
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
            file_path = f"data/{symbol}_{timeframe}_{DAYS_TO_DOWNLOAD}d.csv"
            df.to_csv(file_path)
            print(f"Saved {symbol} data to {file_path}. Rows: {len(df)}")

import requests
import pandas as pd
import time
import os
from datetime import datetime, timedelta

class ToobitDataFetcher:
    def __init__(self):
        self.base_url = 'https://api.toobit.com/quote/v1/klines'
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        
        # Ensure data directory exists
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def fetch_data(self, symbol, timeframe, days=365):
        """
        Fetch historical data from Toobit API.
        Toobit klines endpoint returns up to 1000 candles per request.
        """
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting download for {symbol} ({timeframe}) from Toobit...")
        
        limit = 1000
        end_time_ms = int(time.time() * 1000)
        start_time_ms = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        all_data = []
        
        while end_time_ms > start_time_ms:
            params = {
                'symbol': symbol,
                'interval': timeframe,
                'limit': limit,
                'endTime': end_time_ms
            }
            
            try:
                response = requests.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    print(f"No more data returned for {symbol}.")
                    break
                    
                all_data = data + all_data
                
                # The oldest candle is the first element in the returned list
                oldest_in_batch = data[0][0]
                
                print(f"Fetched {len(data)} candles. Oldest in batch: {datetime.fromtimestamp(oldest_in_batch/1000).strftime('%Y-%m-%d %H:%M')}")
                
                if oldest_in_batch <= start_time_ms:
                    break
                    
                # Update end_time for the next pagination request
                end_time_ms = oldest_in_batch - 1
                
                # Respect API rate limits
                time.sleep(0.2)
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching data: {e}")
                time.sleep(5)  # Wait before retrying
                continue
                
        # Process and save data
        if all_data:
            df = pd.DataFrame(all_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume'
            ])
            
            # Convert timestamp to datetime and set as index
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Keep only standard columns (matching Binance data structure)
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            # Convert string numbers to float
            for col in df.columns:
                df[col] = df[col].astype(float)
                
            # Filter exactly to the requested start_time
            start_date = datetime.now() - timedelta(days=days)
            df = df[df.index >= start_date]
            
            # Remove duplicate indices if any (sometimes happens with pagination)
            df = df[~df.index.duplicated(keep='first')]
            
            filename = f"toobit_{symbol}_{timeframe}_{days}d.csv"
            filepath = os.path.join(self.data_dir, filename)
            df.to_csv(filepath)
            
            print(f"Successfully saved {len(df)} candles to {filename}")
            return df
        else:
            print(f"Failed to fetch any data for {symbol}.")
            return None

if __name__ == "__main__":
    fetcher = ToobitDataFetcher()
    
    # Configuration matches user request
    SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'PEPEUSDT', 'AVAUSDT', 'DOGEUSDT', 'LTCUSDT']
    TIMEFRAME = '30m'
    DAYS_TO_DOWNLOAD = 180  # 6 months as requested previously
    
    for symbol in SYMBOLS:
        fetcher.fetch_data(symbol, TIMEFRAME, DAYS_TO_DOWNLOAD)
        print("-" * 50)

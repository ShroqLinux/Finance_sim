import yfinance as yf
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def get_data(symbol):
    try:
        # Calculate exactly 5 years ago from today
        # five_years_ago = (datetime.now() - relativedelta(years=5)).strftime('%Y-%m-%d')
        
        df = yf.download(symbol, period="5y", interval="1mo")
        if df.empty: return []
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        if 'Date' not in df.columns and 'index' in df.columns: 
            df = df.rename(columns={'index': 'Date'})
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        df = df.rename(columns={'Close': 'price', 'Date': 'date'})
        return df[['date', 'price']].dropna().to_dict('records')
    except Exception as e:
        print(f"Data Fetch Error: {e}")
        return []
import pandas as pd

def cal_cal_average_amount(df, average_date=[5]):
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    if 5 in average_date:
        df['m5'] = df['close'].rolling(window=5).mean()
    if 10 in average_date:
        df['m10'] = df['close'].rolling(window=10).mean()
    if 20 in average_date:
        df['m20'] = df['close'].rolling(window=20).mean()
    if 60 in average_date:
        df['m60'] = df['close'].rolling(window=60).mean()
    if 120 in average_date:
        df['m120'] = df['close'].rolling(window=120).mean()
    return df



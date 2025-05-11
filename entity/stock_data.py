import base_entity

class StockData(base_entity.BaseEntity):
    def __init__(self, ts_code, trade_date, close, open, high, low, pre_close, change, pct_chg, vol, amount):
        self.ts_code = ts_code
        self.trade_date = trade_date
        self.close = close
        self.open = open
        self.high = high
        self.low = low
        self.pre_close = pre_close
        self.change = change
        self.pct_chg = pct_chg
        self.vol = vol
        self.amount = amount
from entity.base_entity import BaseEntity


class StockData(BaseEntity):
    def __init__(self, ts_code, trade_date, close, open, high, low, pre_close, change, pct_chg, vol, amount,
                 average_date, average_amount, deviation_rate, name):
        super().__init__()
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
        self.average_date = average_date
        self.average_amount = average_amount
        self.deviation_rate = deviation_rate
        self.name = name
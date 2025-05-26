from entity.base_entity import BaseEntity
from util.class_util import ClassUtil


class StockData(BaseEntity):
    def __init__(self, id, ts_code, trade_date, close, open, high, low, pre_close, change, pct_chg, vol, amount,
                 average_date, average_amount, deviation_rate, name):
        self.id = id
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

    def get_trade_date(self):
        return self.trade_date

    def get_ts_code(self):
        return self.ts_code

    def set_id(self, id):
        self.id = id

from entity.base_entity import BaseEntity


class MarketData(BaseEntity):
    def __init__(self, id=None, trade_date=None, ts_code=None, ts_name=None,
                 total_mv=None, amount=None, vol=None, trans_count=None,
                 pe=None, tr=None, exchange=None, com_count=None,
                 total_share=None, float_share=None,
                 float_mv=None):
        self.id = id
        self.trade_date = trade_date
        self.ts_code = ts_code
        self.ts_name = ts_name
        self.total_mv = total_mv
        self.amount = amount
        self.vol = vol
        self.trans_count = trans_count
        self.pe = pe
        self.tr = tr
        self.exchange = exchange
        self.com_count = com_count
        self.total_share = total_share
        self.float_share = float_share
        self.float_mv = float_mv

    def get_trade_date(self):
        return self.trade_date

    def get_ts_code(self):
        return self.ts_code

    def set_id(self, id):
        self.id = id
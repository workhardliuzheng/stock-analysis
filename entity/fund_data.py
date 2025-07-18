from entity.base_entity import BaseEntity


class FundData(BaseEntity):
    def __init__(self, id=None, ts_code=None, trade_date=None, name=None,
                 pre_close=None, open=None, high=None, low=None, close=None,
                 change=None, pct_chg=None, vol=None, amount=None,
                 m5=None, m10=None, m20=None, m60=None, m120=None):
        self.id = id
        self.ts_code = ts_code
        self.trade_date = trade_date
        self.name = name
        self.pre_close = pre_close
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.change = change
        self.pct_chg = pct_chg
        self.vol = vol
        self.amount = amount
        self.m5 = m5
        self.m10 = m10
        self.m20 = m20
        self.m60 = m60
        self.m120 = m120

    def get_trade_date(self):
        return self.trade_date

    def get_ts_code(self):
        return self.ts_code

    def set_id(self, id):
        self.id = id

    @staticmethod
    def df_to_entity(row):
        entity = FundData(
            id=row['id'],
            ts_code=row['ts_code'],
            trade_date=row['trade_date'],
            name=row['name'],
            pre_close=row['pre_close'],
            open_price=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            change=row['change'],
            pct_chg=row['pct_chg'],
            vol=row['vol'],
            amount=row['amount'],
            m5=row['m5'],
            m10=row['m10'],
            m20=row['m20'],
            m60=row['m60'],
            m120=row['m120'])
        return entity
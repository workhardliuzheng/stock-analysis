from entity.base_entity import BaseEntity
from util.class_util import ClassUtil


class StockData(BaseEntity):
    def __init__(self, id, ts_code, trade_date, close, open, high, low, pre_close, change, pct_chg, vol, amount,
                 average_date, average_amount, deviation_rate, name, pe_weight, pe_ttm_weight, pb_weight, pe, pb,
                 pe_ttm,
                 pe_profit_dedt, pe_profit_dedt_ttm, ma_5, ma_10, ma_20, ma_50, wma_5, wma_10, wma_20, wma_50,
                 macd, macd_signal_line, macd_histogram, rsi, kdj_k, kdj_d, kdj_j, bb_high, bb_mid, bb_low, obv):
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
        self.pe_weight = pe_weight
        self.pe_ttm_weight = pe_ttm_weight
        self.pb_weight = pb_weight
        self.pe = pe
        self.pb = pb
        self.pe_ttm = pe_ttm
        self.pe_profit_dedt = pe_profit_dedt
        self.pe_profit_dedt_ttm = pe_profit_dedt_ttm
        self.ma_5 = ma_5
        self.ma_10 = ma_10
        self.ma_20 = ma_20
        self.ma_50 = ma_50
        self.wma_5 = wma_5
        self.wma_10 = wma_10
        self.wma_20 = wma_20
        self.wma_50 = wma_50
        self.macd = macd
        self.macd_signal_line = macd_signal_line
        self.macd_histogram = macd_histogram
        self.rsi = rsi
        self.kdj_k = kdj_k
        self.kdj_d = kdj_d
        self.kdj_j = kdj_j
        self.bb_high = bb_high
        self.bb_mid = bb_mid
        self.bb_low = bb_low
        self.obv = obv

    def get_trade_date(self):
        return self.trade_date

    def get_ts_code(self):
        return self.ts_code

    def set_id(self, id):
        self.id = id

import json

from entity.base_entity import BaseEntity
from util.class_util import ClassUtil


class StockData(BaseEntity):
    def __init__(self, id=None, ts_code=None, trade_date=None, close=None, open=None, high=None, low=None,
                 pre_close=None, change=None, pct_chg=None, vol=None, amount=None,
                 average_date=None, average_amount=None, deviation_rate=None, name=None,
                 pe_weight=None, pe_ttm_weight=None, pb_weight=None, pe=None, pb=None,
                 pe_ttm=None, pe_profit_dedt=None, pe_profit_dedt_ttm=None,
                 ma_5=None, ma_10=None, ma_20=None, ma_50=None,
                 wma_5=None, wma_10=None, wma_20=None, wma_50=None,
                 macd=None, macd_signal_line=None, macd_histogram=None, rsi=None,
                 kdj_k=None, kdj_d=None, kdj_j=None,
                 bb_high=None, bb_mid=None, bb_low=None, obv=None,
                 cross_signals=None, percentile_ranks=None):
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
        self.cross_signals = cross_signals
        self.percentile_ranks = percentile_ranks

    def get_trade_date(self):
        return self.trade_date

    def get_ts_code(self):
        return self.ts_code

    def set_id(self, id):
        self.id = id

    def get_deviation_rate_dict(self) -> dict:
        """解析 deviation_rate JSON 返回字典"""
        if self.deviation_rate:
            try:
                return json.loads(self.deviation_rate)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def set_deviation_rate_from_dict(self, rate_dict: dict):
        """从字典设置 deviation_rate"""
        self.deviation_rate = json.dumps(rate_dict)

    def get_cross_signals_dict(self) -> dict:
        """解析 cross_signals JSON 返回字典"""
        if self.cross_signals:
            try:
                return json.loads(self.cross_signals)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def set_cross_signals_from_dict(self, signals_dict: dict):
        """从字典设置 cross_signals"""
        self.cross_signals = json.dumps(signals_dict)

    def get_percentile_ranks_dict(self) -> dict:
        """解析 percentile_ranks JSON 返回字典"""
        if self.percentile_ranks:
            try:
                return json.loads(self.percentile_ranks)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def set_percentile_ranks_from_dict(self, ranks_dict: dict):
        """从字典设置 percentile_ranks"""
        self.percentile_ranks = json.dumps(ranks_dict)

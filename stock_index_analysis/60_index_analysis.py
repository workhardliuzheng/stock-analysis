import tushare as ts

TS_CODE_LIST = ['399001.SZ', '399006.SZ', '000001.SH', '000300.SH', '000510.SH', '000688.SH', '000852.SH']

TRADE_START_DATE = '20150501'
class SixtyIndexAnalysis:
    def __init__(self):
        self.

    def init_sixty_index_average_value(self, ts_code):
        pro = ts.pro_api()
        df = pro.index_daily(ts_code=ts_code, start_date='20180101', end_date='20181010')

import tushare as ts
import yaml

from entity import content
from entity.stock_data import StockData
from mysql_connect.common_mapper import CommonMapper
from tu_share_factory.tu_share_factory import TuShareFactory
from util.date_util import TimeUtils

INDEX_FIELDS=["ts_code","trade_date","open","high","low","close","pre_close","change","pct_chg","vol","amount"]
TRADE_CAL_FIELDS= ["exchange","cal_date","is_open","pretrade_date"]
HISTORY_START_DATE = "20150101"
class SixtyIndexAnalysis:

    def sync_history_value(self):
        for ts_code in content.TS_CODE_LIST:
            self.init_sixty_index_average_value(ts_code, HISTORY_START_DATE, TimeUtils.get_current_date_str())
    def sync_today_value(self):
        for ts_code in content.TS_CODE_LIST:
            self.init_sixty_index_average_value(ts_code, TimeUtils.get_current_date_str(), TimeUtils.get_current_date_str())

    def init_sixty_index_average_value(self, ts_code, start_date, end_date):
        pro = TuShareFactory.build_api_client()

        this_loop_date = start_date
        # endDate不包含当天
        while TimeUtils.compare_date_str(this_loop_date, end_date) <= 0 :
            # 停牌日不计算
            exchange = "SZSE" if ts_code.endswith("SZ") else "SSE"
            trade_cal = pro.trade_cal(**{
                "exchange": exchange,
                "cal_date": this_loop_date,
            }, fields=TRADE_CAL_FIELDS)
            if trade_cal['is_open'][0] == 0:
                continue

            # 因为有停牌休息日，计算60日行情往前多推几天，取最近的60天即可，简单点
            date_ago = TimeUtils.get_n_days_before_or_after(this_loop_date, 100, is_before=True)
            daily = pro.index_daily(**{
                    "ts_code": ts_code,
                    "start_date": date_ago,
                    "end_date": TimeUtils.get_n_days_before_or_after(this_loop_date, 1, is_before=False),
                    "limit": 100
                }, fields=INDEX_FIELDS)
            sixty_index_average_value = daily.iloc[0:60]['close'].mean()
            now_days_value = daily.iloc[-1]
            # 生成数据
            stockData = StockData(ts_code=now_days_value['ts_code'],
                                  trade_date = now_days_value['trade_date'],
                                  close=now_days_value['close'],
                                  open=now_days_value['open'],
                                  high=now_days_value['high'],
                                  low=now_days_value['low'],
                                  pre_close=now_days_value['pre_close'],
                                  change=now_days_value['change'],
                                  pct_chg=now_days_value['pct_chg'],
                                  vol=now_days_value['vol'],
                                  amount=now_days_value['amount']/10,
                                  average_date = 60,
                                  average_amount = sixty_index_average_value)
            CommonMapper.insert_base_entity(stockData)





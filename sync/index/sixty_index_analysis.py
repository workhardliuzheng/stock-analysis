import tushare as ts
import yaml

from entity import constant
from entity.stock_data import StockData
from mysql_connect.common_mapper import CommonMapper
from mysql_connect.sixty_index_mapper import SixtyIndexMapper
from tu_share_factory.tu_share_factory import TuShareFactory
from util.date_util import TimeUtils

INDEX_FIELDS=["ts_code","trade_date","open","high","low","close","pre_close","change","pct_chg","vol","amount"]
TRADE_CAL_FIELDS= [
    "exchange",
    "cal_date",
    "is_open",
    "pretrade_date"
]

mapper = SixtyIndexMapper()

class SixtyIndexAnalysis:

    def sync_history_value(self):
        for ts_code in constant.TS_CODE_LIST:
            history_start_date = constant.HISTORY_START_DATE_MAP[ts_code]
            self.init_sixty_index_average_value(ts_code, history_start_date, TimeUtils.get_current_date_str())

    def sync_today_value(self):
        for ts_code in constant.TS_CODE_LIST:
            self.init_sixty_index_average_value(ts_code, TimeUtils.get_current_date_str(), TimeUtils.get_current_date_str())

    def additional_data(self):
        for ts_code in constant.TS_CODE_LIST:
            history_start_date = constant.HISTORY_START_DATE_MAP[ts_code]
            mapper = SixtyIndexMapper()
            max_trade_datetime = mapper.get_max_trade_time(ts_code)
            if max_trade_datetime is None:
                max_trade_date = history_start_date
            else:
                max_trade_date = TimeUtils.date_to_str(max_trade_datetime)
            start_date = TimeUtils.get_n_days_before_or_after(max_trade_date, 1, True)
            self.init_sixty_index_average_value(ts_code, start_date, TimeUtils.get_current_date_str())

    def analyze_future_trend(self, future_days=[5, 10, 20]):

        results = {}

        for days in future_days:
            print(f"\n=== {days}日后走势分析 ===")

            # 计算未来收益率
            future_returns = []
            deviation_ranges = []

            for ts_code in self.data['ts_code'].unique():
                stock_data = self.data[self.data['ts_code'] == ts_code].copy()
                stock_data = stock_data.sort_values('trade_date').reset_index(drop=True)

                for i in range(len(stock_data) - days):
                    current_price = stock_data.iloc[i]['close']
                    future_price = stock_data.iloc[i + days]['close']
                    current_deviation = stock_data.iloc[i]['deviation_rate']

                    if pd.notna(current_deviation) and pd.notna(future_price):
                        future_return = (future_price - current_price) / current_price * 100
                        future_returns.append(future_return)
                        deviation_ranges.append(current_deviation)

            # 创建分析数据框
            analysis_df = pd.DataFrame({
                'deviation_rate': deviation_ranges,
                'future_return': future_returns
            })

            # 按偏离率分组分析
            bins = [-float('inf'), -10, -5, -2, 0, 2, 5, 10, float('inf')]
            labels = ['<-10%', '-10%~-5%', '-5%~-2%', '-2%~0%', '0%~2%', '2%~5%', '5%~10%', '>10%']

            analysis_df['deviation_range'] = pd.cut(analysis_df['deviation_rate'], bins=bins, labels=labels)

            # 统计各区间的未来收益
            range_analysis = analysis_df.groupby('deviation_range')['future_return'].agg([
                'count', 'mean', 'std', 'min', 'max',
                lambda x: (x > 0).sum() / len(x) * 100  # 上涨概率
            ]).round(4)
            range_analysis.columns = ['样本数', '平均收益率%', '收益率标准差', '最小收益率%', '最大收益率%',
                                      '上涨概率%']

            print(range_analysis)
            results[f'{days}days'] = range_analysis

        return results

    def init_sixty_index_average_value(self, ts_code, start_date, end_date):
        pro = TuShareFactory.build_api_client()

        this_loop_date = start_date
        # endDate不包含当天
        while TimeUtils.compare_date_str(this_loop_date, end_date) <= 0 :
            this_loop_end_date = TimeUtils.get_n_days_before_or_after(this_loop_date, 100, is_before=False)
            # 停牌日不计算
            exchange = "SZSE" if ts_code.endswith("SZ") else "SSE"
            trade_cal = pro.trade_cal(**{
                "exchange": exchange,
                "start_date": this_loop_date,
                "end_date": this_loop_end_date
            }, fields=TRADE_CAL_FIELDS)
            trade_cal = trade_cal.sort_index(ascending=False)

            # 获取一段时间的数据
            date_ago = TimeUtils.get_n_days_before_or_after(this_loop_date, 100, is_before=True)
            daily = pro.index_daily(**{
                "ts_code": ts_code,
                "start_date": date_ago,
                "end_date": this_loop_end_date,
                "limit": 250
            }, fields=INDEX_FIELDS)

            if len(daily) < 60:
                this_loop_date = TimeUtils.get_n_days_before_or_after(this_loop_date, 60-len(daily), False)
                continue

            for row in trade_cal.itertuples():
                if row.is_open == 0:
                    continue
                # 取出最近60天的数据
                sixty_date = daily[daily['trade_date'] <= row.cal_date].head(60)

                sixty_index_average_value = sixty_date['close'].mean()
                now_days_value = sixty_date.iloc[0]
                deviation_rate = now_days_value['close'] / sixty_index_average_value - 1
                # 生成数据
                stock_data = StockData(id=None,
                                       ts_code=now_days_value['ts_code'],
                                       trade_date=now_days_value['trade_date'],
                                       close=float(now_days_value['close']),
                                       open=float(now_days_value['open']),
                                       high=float(now_days_value['high']),
                                       low=float(now_days_value['low']),
                                       pre_close=float(now_days_value['pre_close']),
                                       change=float(now_days_value['change']),
                                       pct_chg=float(now_days_value['pct_chg']),
                                       vol=float(now_days_value['vol']),
                                       amount=float(now_days_value['amount'] / 10),
                                       average_date=60,
                                       average_amount=float(sixty_index_average_value),
                                       deviation_rate=float(deviation_rate * 100),
                                       name=constant.TS_CODE_NAME_DICT[ts_code])
                mapper.insert_index(stock_data)
                this_loop_date = row.cal_date





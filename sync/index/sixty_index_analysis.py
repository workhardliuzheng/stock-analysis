from datetime import datetime, timedelta
import time

import pandas as pd
import tushare as ts
import yaml

from entity import constant
from entity.stock_data import StockData
from entity.stock_weight import StockWeight
from mysql_connect.common_mapper import CommonMapper
from mysql_connect.sixty_index_mapper import SixtyIndexMapper
from mysql_connect.stock_weight_mapper import StockWeightMapper
from tu_share_factory.tu_share_factory import TuShareFactory
from util.class_util import ClassUtil
from util.date_util import TimeUtils

INDEX_FIELDS=["ts_code","trade_date","open","high","low","close","pre_close","change","pct_chg","vol","amount"]
TRADE_CAL_FIELDS= [
    "exchange",
    "cal_date",
    "is_open",
    "pretrade_date"
]

mapper = SixtyIndexMapper()
stock_weight_mapper = StockWeightMapper()

class SixtyIndexAnalysis:

    # 同步今日往前的所有书籍
    def sync_history_value(self):
        for ts_code in constant.TS_CODE_LIST:
            history_start_date = constant.HISTORY_START_DATE_MAP[ts_code]
            self.init_sixty_index_average_value(ts_code, history_start_date, TimeUtils.get_current_date_str())

    # 同步今日往的书籍
    def sync_today_value(self):
        for ts_code in constant.TS_CODE_LIST:
            self.init_sixty_index_average_value(ts_code, TimeUtils.get_current_date_str(), TimeUtils.get_current_date_str())

    # 自动同步数据
    def additional_data(self):
        # 同步权重
        sync_weight()
        # 同步指数价值
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
            self.get_index_pe_pb(ts_code, start_date, TimeUtils.get_current_date_str())




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
                                       name=constant.TS_CODE_NAME_DICT[ts_code],
                                       pb_weight=0,
                                       pe_weight=0,
                                       pe_ttm_weight=0,
                                       pe_ttm=0,
                                       pb=0,
                                       pe=0)
                mapper.insert_index(stock_data)
                this_loop_date = row.cal_date

    def additional_pe_data_and_update_mapper(self, index_code, start_date, end_date):
        value = self.get_index_pe_pb(index_code=index_code, start_date=start_date, end_date=end_date)
        for row in value.iterrows():
            stock_data = StockData(id=None,
                                   ts_code=index_code,
                                   trade_date=value['trade_date'],
                                   close=None,
                                   open=None,
                                   high=None,
                                   low=None,
                                   pre_close=None,
                                   change=None,
                                   pct_chg=None,
                                   vol=None,
                                   amount=None,
                                   average_date=None,
                                   average_amount=None,
                                   deviation_rate=None,
                                   name=None,
                                   pb_weight=value['weighted_pb'],
                                   pe_weight=value['weighted_pe'],
                                   pe_ttm_weight=value['weighted_pe_ttm'],
                                   pe_ttm=0,
                                   pb=0,
                                   pe=0)
            mapper.update_by_ts_code_and_trade_date(stock_data, ['pb_weight', 'pe_weight', 'pe_ttm_weight'])

    # 计算指数pb与pe
    def get_index_pe_pb(self, index_code, start_date, end_date):
        pro = TuShareFactory.build_api_client()
        # 将日期字符串转换为datetime对象
        start_date = datetime.strptime(start_date, '%Y%m%d')
        end_date = datetime.strptime(end_date, '%Y%m%d')

        # 初始化结果列表
        result_data = []

        # 存储每个月的成分股及其权重
        monthly_stock_info = {}

        # 循环遍历每个月
        current_month_start = start_date
        while current_month_start <= end_date:
            # 计算当前月份的结束日期
            next_month_start = (current_month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            current_month_end = next_month_start - timedelta(days=1)

            # 获取当前月份的指数成分股及其权重
            stock = stock_weight_mapper.select_by_code_and_trade_round(index_code=index_code,
                                                               start_date=current_month_start.strftime('%Y%m%d'),
                                                               end_date=current_month_end.strftime('%Y%m%d'))
            stock_info = []
            for row in stock:
                stock_data = ClassUtil.create_entities_from_data(StockWeight, row)
                stock_info.append(stock_data.to_dict())
            stock_info = pd.DataFrame(stock_info)

            # 去重并存储
            month_stock_info = stock_info.drop_duplicates(subset='con_code', keep='first')
            monthly_stock_info[current_month_start] = month_stock_info

            # 移动到下一个月
            current_month_start = next_month_start

        # 找到在整个区间内都存在的公司
        common_stocks = set(monthly_stock_info[next(iter(monthly_stock_info))]['con_code'])
        for stocks in monthly_stock_info.values():
            common_stocks.intersection_update(stocks['con_code'])

        # 如果没有共同的公司，则返回空 DataFrame
        if not common_stocks:
            return pd.DataFrame(columns=['trade_date', 'weighted_pe', 'weighted_pe_ttm', 'weighted_pb'])

        # 批量获取指定时间段内所有股票的基本财务数据
        financial_data = []
        for date in pd.date_range(start=start_date, end=end_date).strftime('%Y%m%d'):
            time.sleep(0.5)
            df = pro.daily_basic(trade_date=date, fields='trade_date,ts_code,pe,pe_ttm,pb,total_mv,circ_mv')
            if not df.empty:
                financial_data.append(df)

        if not financial_data:
            return pd.DataFrame(columns=['trade_date', 'weighted_pe', 'weighted_pe_ttm', 'weighted_pb'])

        financial_df = pd.concat(financial_data)
        financial_df = financial_df[financial_df['ts_code'].isin(common_stocks)]

        # 初始化存储每天财务数据的字典
        daily_financial_data = {}

        for _, row in financial_df.iterrows():
            trade_date = row['trade_date']
            con_code = row['ts_code']
            pe = row['pe']
            pe_ttm = row['pe_ttm']
            pb = row['pb']
            total_mv = row['total_mv']
            circ_mv = row['circ_mv']

            if trade_date not in daily_financial_data:
                daily_financial_data[trade_date] = []

            # 只考虑非NaN的total_mv 和 circ_mv
            if pd.notna(total_mv) and pd.notna(circ_mv):
                daily_financial_data[trade_date].append({
                    'ts_code': con_code,
                    'pe': pe,
                    'pe_ttm': pe_ttm,
                    'pb': pb,
                    'total_mv': total_mv,
                    'circ_mv': circ_mv
                })

        # 循环遍历每个月
        current_month_start = start_date
        while current_month_start <= end_date:
            # 计算当前月份的结束日期
            next_month_start = (current_month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            current_month_end = next_month_start - timedelta(days=1)

            # 确保current_month_end不超过end_date
            if current_month_end > end_date:
                current_month_end = end_date

            # 获取当前月份的指数成分股及其权重
            month_stock_info = monthly_stock_info[current_month_start]

            # 过滤出common_stocks的权重
            month_stock_info = month_stock_info[month_stock_info['con_code'].isin(common_stocks)]

            # 计算每天的加权平均PE, PE_TTM 和 PB
            for trade_date, data_list in daily_financial_data.items():
                trade_date_obj = datetime.strptime(trade_date, '%Y%m%d')

                # 仅处理当前月份的数据
                if current_month_start <= trade_date_obj <= current_month_end:
                    financial_df_daily = pd.DataFrame(data_list)

                    # 合并财务数据和权重
                    merged_df = pd.merge(financial_df_daily, month_stock_info[['con_code', 'weight']],
                                         left_on='ts_code', right_on='con_code')

                    # 初始化加权总市值、加权净利润、加权净资产等变量
                    weighted_total_net_profit = 0
                    weighted_total_net_profit_ttm = 0
                    weighted_total_net_assets = 0
                    weighted_total_circ_mv_pe = 0
                    weighted_total_circ_mv_pe_ttm = 0
                    weighted_total_circ_mv_pb = 0

                    for _, row in merged_df.iterrows():
                        weight = row['weight']
                        total_mv = row['total_mv']
                        circ_mv = row['circ_mv']

                        # 计算净利润（如果有PE）
                        if pd.notna(row['pe']):
                            net_profit = total_mv / row['pe']
                            weighted_total_net_profit += net_profit * weight
                            weighted_total_circ_mv_pe += circ_mv * weight

                        # 计算净利润TTM（如果有PE_TTM）
                        if pd.notna(row['pe_ttm']):
                            net_profit_ttm = total_mv / row['pe_ttm']
                            weighted_total_net_profit_ttm += net_profit_ttm * weight
                            weighted_total_circ_mv_pe_ttm += circ_mv * weight

                        # 计算净资产（如果有PB）
                        if pd.notna(row['pb']):
                            net_assets = total_mv / row['pb']
                            weighted_total_net_assets += net_assets * weight
                            weighted_total_circ_mv_pb += circ_mv * weight

                    # 计算加权平均PE, PE_TTM
                    weighted_pe = weighted_total_circ_mv_pe / weighted_total_net_profit if weighted_total_net_profit > 0 else None
                    weighted_pe_ttm = weighted_total_circ_mv_pe_ttm / weighted_total_net_profit_ttm if weighted_total_net_profit_ttm > 0 else None

                    # 计算加权平均PB
                    weighted_pb = weighted_total_circ_mv_pb / weighted_total_net_assets if weighted_total_net_assets > 0 else None

                    result_data.append({
                        'trade_date': trade_date,
                        'weighted_pe': weighted_pe,
                        'weighted_pe_ttm': weighted_pe_ttm,
                        'weighted_pb': weighted_pb
                    })

            # 移动到下一个月
            current_month_start = next_month_start

        return pd.DataFrame(result_data)

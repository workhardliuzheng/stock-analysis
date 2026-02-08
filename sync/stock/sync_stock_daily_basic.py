import time
from datetime import datetime

import pandas as pd
from fontTools.misc.plistlib import end_date

from entity.financial_data import FinancialData
from entity.stock_daily_basic import StockDailyBasic
from mysql_connect.financial_data_mapper import FinancialDataMapper
from mysql_connect.stock_basic_mapper import StockBasicMapper
from mysql_connect.stock_daily_basic_mapper import StockDailyBasicMapper
from tu_share_factory.tu_share_factory import TuShareFactory
from util.class_util import ClassUtil
from util.date_util import TimeUtils


class StockDailyBasicSync:
    """股票日线基础数据同步器"""
    
    TRADE_CAL_FIELDS = ["exchange", "cal_date", "is_open", "pretrade_date"]
    BATCH_SIZE = 100
    
    def __init__(self):
        self.stock_daily_basic_mapper = StockDailyBasicMapper()
        self.stock_basic_mapper = StockBasicMapper()
        self.financial_mapper = FinancialDataMapper()
    
    def sync_all(self):
        """同步所有股票的日线基础数据"""
        end_date = TimeUtils.get_current_date_str()
        ts_codes = self.stock_basic_mapper.get_all_ts_codes()
        for ts_code in ts_codes:
            start_date = self.stock_daily_basic_mapper.select_max_trade_date(ts_code)
            # 往前推93天，因为季度原因，最多延迟一个季度同步
            start_date = TimeUtils.get_n_days_before_or_after(start_date, 93, True) \
                if start_date is not None else '20120101'
            self._fetch_data_batch(ts_code, start_date, end_date)
    
    def _fetch_data_batch(self, ts_code, start_date, end_date):
        """获取单个时间批次的数据"""
        pro = TuShareFactory.build_api_client()
        exchange = "SZSE" if ts_code.endswith("SZ") else "SSE"
        time.sleep(0.2)

        try:
            batch_idx = 0

            daily_basic_df = pro.daily_basic(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                fields=[
                    "ts_code", "trade_date", "close", "turnover_rate", "turnover_rate_f", 
                    "volume_ratio", "pe", "pe_ttm", "pb", "ps", "ps_ttm", "dv_ratio", 
                    "dv_ttm", "total_share", "float_share", "free_share", "total_mv", "circ_mv"
                ]
            )
            
            batch_data = []
            batch_count = 0
            total_processed = 0

            data = self.financial_mapper.select_financial_data_by_ts_code(ts_code=ts_code)
            data_frame_list = []
            for row in data:
                financial_data = ClassUtil.create_entities_from_data(FinancialData, row)
                data_frame_list.append(financial_data.to_dict())
            financial_data_pd = pd.DataFrame(data_frame_list)

            for _, row in daily_basic_df.iterrows():
                pe_profit_dedt = None
                pe_ttm_profit_dedt = None

                # 获取上一年年终扣非净利润
                if financial_data_pd is not None and not financial_data_pd.empty:
                    last_day_of_previous_year = TimeUtils.get_last_day_of_previous_year(row['trade_date'])
                    filtered_data = financial_data_pd[financial_data_pd['end_date'] == TimeUtils.date_to_str(last_day_of_previous_year)]
                    if len(filtered_data) > 0 and 'profit_dedt' in filtered_data.columns and filtered_data['profit_dedt'] is not None:
                        pe_profit_dedt = row['circ_mv'] * 10000 / filtered_data['profit_dedt'].iloc[0]

                    profit_dedt_ttm = self._get_profit_dedt_ttm(financial_data_pd, row['trade_date'])
                    if profit_dedt_ttm is not None:
                        pe_ttm_profit_dedt = row['circ_mv'] * 10000 / profit_dedt_ttm

                daily_data = StockDailyBasic.from_df_row(row)
                daily_data.pe_profit_dedt = pe_profit_dedt if pe_profit_dedt is not None and pe_profit_dedt >= 0 else None
                daily_data.pe_ttm_profit_dedt = pe_ttm_profit_dedt if pe_ttm_profit_dedt is not None and pe_ttm_profit_dedt >= 0 else None

                batch_data.append(daily_data)
                batch_count += 1

                if len(batch_data) >= self.BATCH_SIZE:
                    self.stock_daily_basic_mapper.batch_insert_stock_daily_basic(batch_data)
                    print(f"  第 {batch_idx} 批已处理 {batch_count} 条数据，当前批次插入 {len(batch_data)} 条")
                    total_processed += len(batch_data)
                    batch_data = []
                    batch_idx += 1

            if batch_data:
                self.stock_daily_basic_mapper.batch_insert_stock_daily_basic(batch_data)
                print(f"  第 {batch_idx} 批最后批次插入 {len(batch_data)} 条数据")
                total_processed += len(batch_data)

            print(f"第 {batch_idx} 批处理完成，共处理 {batch_count} 条数据")
        except Exception as e:
            print(f"        批次数据获取失败: {e}, {ts_code}，50秒后重试")
            time.sleep(50)
            self._fetch_data_batch(ts_code, start_date, end_date)
    
    def _get_profit_dedt_ttm(self, data_pd, date):
        """计算TTM扣非净利润"""
        records = data_pd[data_pd['end_date'] <= date]
        records = records.sort_values(by='end_date', ascending=False)
        if len(records) < 5:
            return None
        records = records.head(5)

        last_quarter_date = records.iloc[0]['end_date']
        last_quarter_date_time = TimeUtils.str_to_date(last_quarter_date)
        if last_quarter_date_time.month == 12:
            return records.iloc[0]['profit_dedt']
        else:
            last_year_this_quarter = datetime(
                last_quarter_date_time.year - 1, 
                last_quarter_date_time.month,
                last_quarter_date_time.day
            )
            last_year_this_quarter_str = TimeUtils.date_to_str(last_year_this_quarter)
            last_year_last_date = datetime(last_quarter_date_time.year - 1, 12, 31)
            last_year_last_date_str = TimeUtils.date_to_str(last_year_last_date)
            last_year_data = records[records['end_date'] == last_year_last_date_str]
            last_year_this_quarter_data = records[records['end_date'] == last_year_this_quarter_str]

            if (last_year_data is not None and last_year_this_quarter_data is not None
                    and not last_year_data.empty and not last_year_this_quarter_data.empty):
                return records['profit_dedt'].iloc[0] + last_year_data['profit_dedt'].iloc[0] - last_year_this_quarter_data['profit_dedt'].iloc[0]
            else:
                return None

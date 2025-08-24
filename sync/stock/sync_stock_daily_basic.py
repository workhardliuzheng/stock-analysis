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

stock_daily_basic_mapper = StockDailyBasicMapper()
stock_basic_mapper = StockBasicMapper()
financial_mapper = FinancialDataMapper()
TRADE_CAL_FIELDS= [
    "exchange",
    "cal_date",
    "is_open",
    "pretrade_date"
]


def sync_all_stock_basic_daily():
    end_date = TimeUtils.get_current_date_str()
    ts_codes = stock_basic_mapper.get_all_ts_codes()
    for ts_code in ts_codes:
        start_date = stock_daily_basic_mapper.select_max_trade_date(ts_code)
        # 往前推93天，因为季度原因，最多延迟一个季度同步，因此进一个季度需要更新书籍
        start_date = TimeUtils.get_n_days_before_or_after(start_date, 93, True) \
            if start_date is not None else '20120101'
        _fetch_financial_data_batch(ts_code, start_date, end_date)



def _fetch_financial_data_batch(ts_code, start_date, end_date):
    """
    获取单个时间批次的财务数据

    Args:
        pro: TuShare API客户端
        ts_code: 股票代码
        start_date: 开始日期 (datetime对象)
        end_date: 结束日期 (datetime对象)

    Returns:
        dict: 财务数据 {date: data}
    """
    pro = TuShareFactory.build_api_client()
    exchange = "SZSE" if ts_code.endswith("SZ") else "SSE"
    time.sleep(0.2)

    try:
        batch_idx = 0

        # 获取当前批次的每日基础数据
        daily_basic_df = pro.daily_basic(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields=[ "ts_code", "trade_date", "close", "turnover_rate", "turnover_rate_f", "volume_ratio", "pe", "pe_ttm",
                     "pb", "ps", "ps_ttm", "dv_ratio", "dv_ttm", "total_share", "float_share", "free_share", "total_mv", "circ_mv"]
        )
        BATCH_SIZE = 100
        # 准备批量数据
        batch_data = []
        batch_count = 0
        total_processed = 0

        data = financial_mapper.select_financial_data_by_ts_code(ts_code=ts_code)
        data_frame_list = []
        for row in data:
            financial_data = ClassUtil.create_entities_from_data(FinancialData, row)
            data_frame_list.append(financial_data.to_dict())
        financial_data_pd = pd.DataFrame(data_frame_list)

        for _, row in daily_basic_df.iterrows():
            pe_profit_dedt = None
            pe_ttm_profit_dedt = None

            #获取上一年年终扣非净利润
            last_day_of_previous_year = TimeUtils.get_last_day_of_previous_year(row['trade_date'])
            filtered_data = financial_data_pd[financial_data_pd['end_date'] == TimeUtils.date_to_str(last_day_of_previous_year)]
            if len(filtered_data) > 0 and 'profit_dedt' in filtered_data.columns and filtered_data['profit_dedt'] is not None:
                pe_profit_dedt = row['circ_mv'] * 10000 / filtered_data['profit_dedt'].iloc[0]

            profit_dedt_ttm = _get_profit_dedt_ttm(financial_data_pd, row['trade_date'])
            if profit_dedt_ttm is not None:
                pe_ttm_profit_dedt = row['circ_mv'] * 10000 / profit_dedt_ttm

            # 创建每日基础数据对象（这里需要根据你的实体类调整）
            daily_data = StockDailyBasic(id=None,
                                         ts_code=row['ts_code'],
                                         trade_date=row['trade_date'],
                                         close=row['close'] if pd.notna(row['close']) else None,
                                         turnover_rate=row['turnover_rate'] if pd.notna(row['turnover_rate']) else None,
                                         turnover_rate_f=row['turnover_rate_f'] if pd.notna
                                             (row['turnover_rate_f']) else None,
                                         volume_ratio=row['volume_ratio'] if pd.notna(row['volume_ratio']) else None,
                                         pe=row['pe'] if pd.notna(row['pe']) else None,
                                         pe_ttm=row['pe_ttm'] if pd.notna(row['pe_ttm']) else None,
                                         pb=row['pb'] if pd.notna(row['pb']) else None,
                                         ps=row['ps'] if pd.notna(row['ps']) else None,
                                         ps_ttm=row['ps_ttm'] if pd.notna(row['ps_ttm']) else None,
                                         dv_ratio=row['dv_ratio'] if pd.notna(row['dv_ratio']) else None,
                                         dv_ttm=row['dv_ttm'] if pd.notna(row['dv_ttm']) else None,
                                         total_share=row['total_share'] if pd.notna(row['total_share']) else None,
                                         float_share=row['float_share'] if pd.notna(row['float_share']) else None,
                                         free_share=row['free_share'] if pd.notna(row['free_share']) else None,
                                         total_mv=row['total_mv'] if pd.notna(row['total_mv']) else None,
                                         circ_mv=row['circ_mv'] if pd.notna(row['circ_mv']) else None,
                                         pe_profit_dedt=pe_profit_dedt if pe_profit_dedt is not None and pe_profit_dedt >= 0 else None,
                                         pe_ttm_profit_dedt=pe_ttm_profit_dedt if pe_ttm_profit_dedt is not None and pe_ttm_profit_dedt >= 0 else None
                                         )

            batch_data.append(daily_data)
            batch_count += 1

            # 当达到批量大小时，执行批量插入
            if len(batch_data) >= BATCH_SIZE:
                stock_daily_basic_mapper.batch_insert_stock_daily_basic(batch_data)  # 假设你有对应的mapper
                print(f"  第 {batch_idx} 批已处理 {batch_count} 条数据，当前批次插入 {len(batch_data)} 条")
                total_processed += len(batch_data)
                batch_data = []  # 清空批量数据
                batch_idx += 1

        # 处理剩余的数据
        if batch_data:
            stock_daily_basic_mapper.batch_insert_stock_daily_basic(batch_data)
            print(f"  第 {batch_idx} 批最后批次插入 {len(batch_data)} 条数据")
            total_processed += len(batch_data)

        print(f"第 {batch_idx} 批处理完成，共处理 {batch_count} 条数据")
    except Exception as e:
        print(f"        批次数据获取失败: {e}, {ts_code}")
        time.sleep(50)
        _fetch_financial_data_batch(ts_code, start_date, end_date)


def _get_profit_dedt_ttm(data_pd, date):
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
        last_year_this_quarter = datetime(last_quarter_date_time.year - 1, last_quarter_date_time.month,
                                          last_quarter_date_time.day)
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

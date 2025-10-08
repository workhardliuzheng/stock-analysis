# 自动同步数据
import time
from datetime import datetime, timedelta
import pandas as pd

from entity import constant
from entity.financing_margin_trading import FinancingMarginTrading
from mysql_connect.financing_margin_trading_mapper import FinancingMarginTradingMapper
from mysql_connect.stock_basic_mapper import StockBasicMapper
from tu_share_factory.tu_share_factory import TuShareFactory
from util.date_util import TimeUtils

mapper = FinancingMarginTradingMapper()
stock_basic_mapper = StockBasicMapper()

FINANCING_MARGIN_TRADING_FIELDS = [
    "trade_date", "exchange_id", "rzye", "rzmre", "rzche", "rqye", "rqmcl", "rzrqye", "rqyl"
]


def additional_data():
    start_date = mapper.get_max_trade_date(exchange_id=None)
    start_date = start_date if start_date else '19000101'
    time.sleep(0.3)
    try:
        sync_financing_margin_trading(start_date, TimeUtils.get_current_date_str())
    except Exception as e:
        time.sleep(30)
        sync_financing_margin_trading(start_date, TimeUtils.get_current_date_str())

def init():
    current_year = datetime.now().year
    start_year = 2015

    while start_year <= current_year:
        year_start = datetime(start_year, 1, 1)
        year_end = datetime(start_year, 12, 31)

        try:
            sync_financing_margin_trading(TimeUtils.date_to_str(year_start), TimeUtils.date_to_str(year_end))
        except Exception as e:
            time.sleep(30)
            sync_financing_margin_trading(TimeUtils.date_to_str(year_start), TimeUtils.date_to_str(year_end))
        start_year += 1

def sync_financing_margin_trading(start_date, end_date):
    pro = TuShareFactory.build_api_client()

    # 批量大小
    BATCH_SIZE = 100

    financing_info = pro.margin(start_date=start_date, end_date=end_date, fields=FINANCING_MARGIN_TRADING_FIELDS)

    # 准备批量数据
    batch_data = []
    total_count = 0

    for _, row in financing_info.iterrows():
        # 生成数据
        financing_margin_trading = FinancingMarginTrading(
            id=None,
            trade_date=row['trade_date'] if pd.notna(row['trade_date']) else None,
            exchange_id=row['exchange_id'] if pd.notna(row['exchange_id']) else None,
            rzye=row['rzye'] if pd.notna(row['rzye']) else None,
            rzmre=row['rzmre'] if pd.notna(row['rzmre']) else None,
            rzche=row['rzche'] if pd.notna(row['rzche']) else None,
            rqye=row['rqye'] if pd.notna(row['rqye']) else None,
            rqmcl=row['rqmcl'] if pd.notna(row['rqmcl']) else None,
            rzrqye=row['rzrqye'] if pd.notna(row['rzrqye']) else None,
            rqyl=row['rqyl'] if pd.notna(row['rqyl']) else None
        )
        batch_data.append(financing_margin_trading)
        total_count += 1

        # 当达到批量大小时，执行批量插入
        if len(batch_data) >= BATCH_SIZE:
            mapper.insert_financing_margin_trading_batch(batch_data)
            print(f"已处理 {total_count} 条数据，当前批次插入 {len(batch_data)} 条")
            batch_data = []  # 清空批量数据

    # 处理剩余的数据（不足100条的最后一批）
    if batch_data:
        mapper.insert_financing_margin_trading_batch(batch_data)



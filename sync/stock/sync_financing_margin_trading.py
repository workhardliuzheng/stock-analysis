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


class FinancingMarginTradingSync:
    """融资融券数据同步器"""
    
    FIELDS = [
        "trade_date", "exchange_id", "rzye", "rzmre", "rzche", "rqye", "rqmcl", "rzrqye", "rqyl"
    ]
    BATCH_SIZE = 100
    
    def __init__(self):
        self.mapper = FinancingMarginTradingMapper()
    
    def additional_data(self):
        """增量同步"""
        start_date = self.mapper.get_max_trade_date(exchange_id=None)
        start_date = start_date if start_date else '19000101'
        time.sleep(0.3)
        try:
            self._sync_data(start_date, TimeUtils.get_current_date_str())
        except Exception as e:
            print(f'同步融资融券数据失败: {e}，30秒后重试')
            time.sleep(30)
            self._sync_data(start_date, TimeUtils.get_current_date_str())
    
    def init(self):
        """全量初始化 2015年至今"""
        current_year = datetime.now().year
        start_year = 2015

        while start_year <= current_year:
            year_start = datetime(start_year, 1, 1)
            year_end = datetime(start_year, 12, 31)

            try:
                self._sync_data(TimeUtils.date_to_str(year_start), TimeUtils.date_to_str(year_end))
            except Exception as e:
                print(f'同步 {start_year} 年融资融券数据失败: {e}，30秒后重试')
                time.sleep(30)
                self._sync_data(TimeUtils.date_to_str(year_start), TimeUtils.date_to_str(year_end))
            start_year += 1
    
    def _sync_data(self, start_date, end_date):
        """内部同步实现"""
        pro = TuShareFactory.build_api_client()
        financing_info = pro.margin(start_date=start_date, end_date=end_date, fields=self.FIELDS)

        batch_data = []
        total_count = 0

        for _, row in financing_info.iterrows():
            financing_margin_trading = FinancingMarginTrading.from_df_row(row)
            batch_data.append(financing_margin_trading)
            total_count += 1

            if len(batch_data) >= self.BATCH_SIZE:
                self.mapper.insert_financing_margin_trading_batch(batch_data)
                print(f"已处理 {total_count} 条数据，当前批次插入 {len(batch_data)} 条")
                batch_data = []

        if batch_data:
            self.mapper.insert_financing_margin_trading_batch(batch_data)
            print(f"最后批次插入 {len(batch_data)} 条数据")



# 自动同步数据
import time
from datetime import datetime, timedelta

from entity import constant
from entity.stock_weight import StockWeight
from mysql_connect.stock_weight_mapper import StockWeightMapper
from tu_share_factory.tu_share_factory import TuShareFactory
from util.date_util import TimeUtils


class StockWeightSync:
    """指数成分股权重数据同步器"""
    
    BATCH_SIZE = 100
    
    def __init__(self):
        self.mapper = StockWeightMapper()
    
    def additional_data(self):
        """增量同步所有指数的权重数据"""
        for ts_code in constant.TS_CODE_LIST:
            history_start_date = constant.HISTORY_START_DATE_MAP[ts_code]
            max_trade_datetime = self.mapper.get_max_trade_time(ts_code)
            if max_trade_datetime is None:
                max_trade_date = history_start_date
            else:
                max_trade_date = max_trade_datetime
            start_date = TimeUtils.get_n_days_before_or_after(max_trade_date, 1, True)
            self._sync_data(ts_code, start_date, TimeUtils.get_current_date_str())
    
    def _sync_data(self, index_code, start_date, end_date):
        """同步单个指数的权重数据"""
        pro = TuShareFactory.build_api_client()
        
        # 将日期字符串转换为datetime对象
        start_date = datetime.strptime(start_date, '%Y%m%d')
        end_date = datetime.strptime(end_date, '%Y%m%d')

        # 循环遍历每个月
        current_month_start = start_date
        while current_month_start <= end_date:
            # 计算当前月份的结束日期
            next_month_start = (current_month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            current_month_end = next_month_start - timedelta(days=1)

            # 获取当前月份的指数成分股及其权重
            time.sleep(0.3)
            stock_info = pro.index_weight(
                index_code=index_code, 
                start_date=current_month_start.strftime('%Y%m%d'),
                end_date=current_month_end.strftime('%Y%m%d')
            )

            # 去重并存储
            month_stock_info = stock_info.drop_duplicates(subset='con_code', keep='first')

            batch_data = []
            total_count = 0

            for _, row in month_stock_info.iterrows():
                stock_data = StockWeight.from_df_row(row)
                batch_data.append(stock_data)
                total_count += 1

                if len(batch_data) >= self.BATCH_SIZE:
                    self.mapper.insert_index_batch(batch_data)
                    print(f"已处理 {total_count} 条数据，当前批次插入 {len(batch_data)} 条")
                    batch_data = []

            if batch_data:
                self.mapper.insert_index_batch(batch_data)
                print(f"最后批次插入 {len(batch_data)} 条数据")

            print(f"月份 {current_month_start.strftime('%Y-%m')} 处理完成，共处理 {total_count} 条数据")

            # 移动到下一个月
            current_month_start = next_month_start

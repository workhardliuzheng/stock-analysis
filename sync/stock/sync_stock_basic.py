from datetime import datetime, timedelta
import pandas as pd

from entity.stock_basic import StockBasic
from mysql_connect.stock_basic_mapper import StockBasicMapper
from tu_share_factory.tu_share_factory import TuShareFactory


class StockBasicSync:
    """股票基础信息同步器"""
    
    BATCH_SIZE = 100
    
    def __init__(self):
        self.mapper = StockBasicMapper()
    
    def sync_all(self):
        """同步所有股票基础信息"""
        try:
            # 获取所有上市状态的股票
            self._sync_by_status('L')  # 上市
            self._sync_by_status('D')  # 退市
            self._sync_by_status('P')  # 暂停上市
            print("股票基础信息同步完成")
        except Exception as e:
            print(f"同步股票基础信息失败: {e}")
    
    def _sync_by_status(self, list_status='L'):
        """
        根据上市状态同步股票基础信息
        :param list_status: L上市 D退市 P暂停上市
        """
        pro = TuShareFactory.build_api_client()

        try:
            print(f"开始获取上市状态为 {list_status} 的股票基础信息...")
            stock_basic_df = pro.stock_basic(
                exchange='',
                list_status=list_status,
                fields='ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs'
            )

            if stock_basic_df.empty:
                print(f"未获取到上市状态为 {list_status} 的股票数据")
                return

            print(f"获取到 {len(stock_basic_df)} 条股票基础信息")
            self._batch_process(stock_basic_df)

        except Exception as e:
            print(f"获取股票基础信息失败: {e}")
            raise
    
    def _batch_process(self, stock_basic_df):
        """批量处理股票基础信息"""
        batch_data = []
        total_count = 0

        for _, row in stock_basic_df.iterrows():
            stock_basic = StockBasic.from_df_row(row)
            batch_data.append(stock_basic)
            total_count += 1

            if len(batch_data) >= self.BATCH_SIZE:
                self.mapper.upsert_stock_basic_batch(batch_data)
                print(f"已处理 {total_count} 条数据，当前批次处理 {len(batch_data)} 条")
                batch_data = []

        if batch_data:
            self.mapper.upsert_stock_basic_batch(batch_data)
            print(f"最后批次处理 {len(batch_data)} 条数据")

        print(f"股票基础信息处理完成，共处理 {total_count} 条数据")
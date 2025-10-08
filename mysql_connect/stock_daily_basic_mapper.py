from mysql_connect.common_mapper import CommonMapper
from util.date_util import TimeUtils


class StockDailyBasicMapper(CommonMapper):
    def __init__(self):
        super().__init__('stock_daily_basic')
        self.table_name = 'stock_daily_basic'

    def insert_stock_daily_basic(self, stock_daily_basic):
        trade_date = stock_daily_basic.get_trade_date()
        ts_code = stock_daily_basic.get_ts_code()
        value = self.select_by_trade_date(ts_code, trade_date)
        if value is not None and value:
            print('编码为' + ts_code + '交易时间为' + TimeUtils.date_to_str(trade_date) + '存在重复数据')
        else:
            self.insert_base_entity(stock_daily_basic)

    def batch_insert_stock_daily_basic(self, stock_daily_basics):
        """
        使用数据库 UPSERT 功能批量插入股票每日基本面数据

        Args:
            stock_daily_basics: list of StockDailyBasic objects or single StockDailyBasic object
        """
        # 处理单个对象的情况
        if not isinstance(stock_daily_basics, list):
            stock_daily_basics = [stock_daily_basics]

        if not stock_daily_basics:
            return

        # 内存去重
        unique_data = {}
        duplicate_count = 0

        for stock_daily_basic in stock_daily_basics:
            ts_code = stock_daily_basic.get_ts_code()
            trade_date = stock_daily_basic.get_trade_date()

            key = (ts_code, trade_date)
            if key in unique_data:
                duplicate_count += 1
                print(f'内存中发现重复数据：编码为{ts_code}，交易时间为{trade_date}')
            else:
                unique_data[key] = stock_daily_basic

        valid_data = list(unique_data.values())

        if valid_data:
            # 使用 UPSERT 批量插入（需要实现 upsert 方法）
            inserted_count = self.upsert_base_entities_batch(valid_data)
            print(f'处理 {len(valid_data)} 条股票每日基本面数据，实际插入 {inserted_count} 条新数据')

        if duplicate_count > 0:
            print(f'内存去重跳过 {duplicate_count} 条重复数据')

    def delete_all(self):
        """全量删除所有数据"""
        self.delete_by_condition('1=1')
        print('已删除所有股票每日基本面数据')

    def delete_by_trade_date(self, trade_date):
        """根据交易日期删除数据"""
        condition = f'trade_date = \'{trade_date}\''
        self.delete_by_condition(condition=condition)
        print(f'已删除交易日期为{trade_date}的所有数据')

    def delete_by_ts_code(self, ts_code):
        """根据交易日期删除数据"""
        condition = f'ts_code = \'{ts_code}\''
        self.delete_by_condition(condition=condition)
        print(f'已删除交易日期为{ts_code}的所有数据')

    def select_by_trade_date(self, trade_date):
        """根据股票代码和交易日期查询"""
        condition = f'trade_date = \'{trade_date}\''
        stock_data = self.select_base_entity(columns='*', condition=condition)
        return stock_data

    def select_by_trade_date_and_ts_code(self, trade_date, ts_code_list):
        """根据股票代码和交易日期查询"""
        placeholders = ', '.join(f'\'{code}\'' for code in ts_code_list)
        condition = f'trade_date = \'{trade_date}\' and ts_code IN ({placeholders})'
        stock_data = self.select_base_entity(columns='*', condition=condition)
        return stock_data

    def select_max_trade_date(self, ts_code):
        """根据股票代码和交易日期查询"""
        condition = f'ts_code = \'{ts_code}\''
        stock_data = self.select_base_entity(columns='MAX(trade_date)', condition=condition)
        return stock_data[0][0]

    def select_by_ts_code(self, ts_code=''):
        """根据股票代码查询"""
        condition = f'ts_code = \'{ts_code}\''
        stock_data = self.select_base_entity(columns='*', condition=condition)
        return stock_data

    def select_by_code_and_trade_round(self, ts_code, start_date, end_date):
        """根据股票代码和交易日期范围查询"""
        condition = f'ts_code = \'{ts_code}\' and trade_date >= \'{start_date}\' and trade_date <= \'{end_date}\''
        data = self.select_base_entity(columns='*', condition=condition)
        return data

    def select_by_trade_date_range(self, start_date, end_date):
        """根据交易日期范围查询所有股票数据"""
        condition = f'trade_date >= \'{start_date}\' and trade_date <= \'{end_date}\''
        data = self.select_base_entity(columns='*', condition=condition)
        return data

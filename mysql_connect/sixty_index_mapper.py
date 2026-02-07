from entity import constant
from mysql_connect.common_mapper import CommonMapper


class SixtyIndexMapper(CommonMapper):
    def __init__(self):
        super().__init__('ts_stock_data')
        self.table_name = 'ts_stock_data'

    def insert_index(self, sixty_index):
        trade_date = sixty_index.get_trade_date()
        ts_code = sixty_index.get_ts_code()
        value = self.select_sixty_index_by_trade_date(ts_code, trade_date)
        if value is not None and value:
            print('编码为' + ts_code + '交易时间为' + trade_date + '存在重复数据')
        else:
            self.insert_base_entity(sixty_index)


    # 根据指数编码和时间获取数据
    def select_sixty_index_by_trade_date(self, ts_code, trade_date):
        condition = f'ts_code = \'{ts_code}\' and trade_date = \'{trade_date}\''
        sixty_index = self.select_base_entity(columns='*', condition=condition)
        return sixty_index

    def get_max_trade_time(self, ts_code):
        # 构建 SQL 查询以获取最大交易时间
        query = f" ts_code = \'{ts_code}\';"
        # 执行查询
        sixty_index = self.select_base_entity(columns='MAX(trade_date)', condition=query)
        return sixty_index[0][0]

    def select_by_code_and_trade_round(self, ts_code, start_date, end_date):

        condition = f'ts_code = \'{ts_code}\' and trade_date >= \'{start_date}\' and trade_date <= \'{end_date}\''
        sixty_index = self.select_base_entity(columns='*', condition=condition)
        return sixty_index

    def update_by_ts_code_and_trade_date(self, base_entity, columns):
        self.update_base_entity(base_entity, columns, ['ts_code', 'trade_date'])

    def upsert_batch(self, stock_data_list: list):
        """
        批量插入或更新指数数据
        
        使用 ON DUPLICATE KEY UPDATE 实现 upsert
        前提：ts_stock_data 表需要有 (ts_code, trade_date) 唯一索引
        
        Args:
            stock_data_list: StockData 对象列表
        """
        if not stock_data_list:
            return
        
        # 使用 CommonMapper 的 upsert 方法
        self.upsert_base_entities_batch(stock_data_list)

    def batch_update_by_ts_code_and_trade_date(self, stock_data_list: list, columns: list):
        """
        批量更新指数数据
        
        Args:
            stock_data_list: StockData 对象列表
            columns: 要更新的列名列表
        """
        for stock_data in stock_data_list:
            self.update_by_ts_code_and_trade_date(stock_data, columns)
from mysql_connect.common_mapper import CommonMapper


class StockWeightMapper(CommonMapper):
    def __init__(self):
        super().__init__('stock_weight')
        self.table_name = 'stock_weight'

    def insert_index(self, stock_weight):
        index_code = stock_weight.get_index_code()
        con_code = stock_weight.get_con_code()
        trade_date = stock_weight.get_trade_date()
        value = self.select_weight_by_index_con_trade_date(index_code, con_code, trade_date)
        if value is not None and value:
            print('编码为' + con_code + '交易时间为' + trade_date + '存在重复数据')
        else:
            self.insert_base_entity(stock_weight)


    # 根据指数编码和时间获取数据
    def select_weight_by_index_con_trade_date(self, index_code, con_code, trade_date):
        condition = f'index_code = \'{index_code}\' and trade_date = \'{trade_date}\' and con_code = \'{con_code}\''
        sixty_index = self.select_base_entity(columns='*', condition=condition)
        return sixty_index


    def select_by_code_and_trade_round(self, index_code, start_date, end_date):

        condition = f'index_code = \'{index_code}\' and trade_date >= \'{start_date}\' and trade_date <= \'{end_date}\''
        sixty_index = self.select_base_entity(columns='*', condition=condition)
        return sixty_index

    def get_max_trade_time(self, index_code):
        # 构建 SQL 查询以获取最大交易时间
        query = f" index_code = \'{index_code}\';"
        # 执行查询
        sixty_index = self.select_base_entity(columns='MAX(trade_date)', condition=query)
        return sixty_index[0][0]
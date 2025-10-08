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

    def insert_index_batch(self, stock_weights):
        """
        使用数据库 UPSERT 功能批量插入

        Args:
            stock_weights: list of stock_weight objects or single stock_weight object
        """
        # 处理单个对象的情况
        if not isinstance(stock_weights, list):
            stock_weights = [stock_weights]

        if not stock_weights:
            return

        # 内存去重
        unique_data = {}
        duplicate_count = 0

        for stock_weight in stock_weights:
            index_code = stock_weight.get_index_code()
            con_code = stock_weight.get_con_code()
            trade_date = stock_weight.get_trade_date()

            key = (index_code, con_code, trade_date)
            if key in unique_data:
                duplicate_count += 1
            else:
                unique_data[key] = stock_weight

        valid_data = list(unique_data.values())

        if valid_data:
            # 使用 UPSERT 批量插入（需要实现 upsert 方法）
            inserted_count = self.upsert_base_entities_batch(valid_data)
            print(f'处理 {len(valid_data)} 条数据，实际插入 {inserted_count} 条新数据')

        if duplicate_count > 0:
            print(f'内存去重跳过 {duplicate_count} 条重复数据')


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

    def get_exist_con_code(self, index_code, start_date, end_date):
        """
        根据最新的权重获取在这个区间内均存在的股票
        """
        new_trade_date = self.get_max_trade_time(index_code=index_code)

        sql = f"""
            SELECT con_code
            FROM stock_weight
            WHERE index_code = '{index_code}'
              AND trade_date = '{new_trade_date}'
              AND con_code IN (
                SELECT ts_code 
                FROM stock_basic 
                WHERE list_date <= '{start_date}'  
                  AND (delist_date IS NULL OR delist_date > '{end_date}')
              );
            """
        result = self.execute_sql(sql)
        return [row[0] for row in result]

    def get_newest_weight_by_con_code_list(self, index_code, con_code_list, start_date, end_date):
        # 将列表转换为逗号分隔的字符串
        placeholders = ', '.join(f'\'{code}\'' for code in con_code_list)
        new_trade_date = self.get_max_trade_time(index_code=index_code)
        # 构建 SQL 查询以获取 con_code
        query = (f"con_code IN ({placeholders}) and trade_date = \'{new_trade_date}\' "
                 f"and index_code=\'{index_code}\'")
        return self.select_base_entity(columns='*', condition=query)

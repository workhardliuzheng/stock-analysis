from mysql_connect.common_mapper import CommonMapper

class MarketDataMapper(CommonMapper):
    def __init__(self):
        super().__init__('market_data')
        self.table_name = 'market_data'

    def insert_market_data(self, market_data):
        trade_date = market_data.get_trade_date()
        value = self.select_market_data_by_trade_date(trade_date)
        if value is not None and value:
            print(f'交易日期为{trade_date}存在重复数据')
        else:
            self.insert_base_entity(market_data)

    def insert_market_data_batch(self, market_datas):
        """
        使用数据库 UPSERT 功能批量插入

        Args:
            market_datas: list of MarketData objects or single MarketData object
        """
        # 处理单个对象的情况
        if not isinstance(market_datas, list):
            market_datas = [market_datas]

        if not market_datas:
            return

        # 内存去重
        unique_data = {}
        duplicate_count = 0

        for market_data in market_datas:
            trade_date = market_data.get_trade_date()

            key = trade_date
            if key in unique_data:
                duplicate_count += 1
            else:
                unique_data[key] = market_data

        valid_data = list(unique_data.values())

        if valid_data:
            # 使用 UPSERT 批量插入（需要实现 upsert 方法）
            inserted_count = self.upsert_base_entities_batch(valid_data)
            print(f'处理 {len(valid_data)} 条数据，实际插入 {inserted_count} 条新数据')

        if duplicate_count > 0:
            print(f'内存去重跳过 {duplicate_count} 条重复数据')

    # 根据交易键获取数据
    def select_market_data_by_trade_date(self, trade_date):
        condition = (
            f"trade_date = '{trade_date}'"
        )
        result = self.select_base_entity(columns='*', condition=condition)
        return result

    def select_all_market_data(self):
        result = self.select_base_entity(columns='*')
        return result

    def select_by_date_range(self, start_date, end_date):
        condition = (
            f"trade_date >= '{start_date}' AND "
            f"trade_date <= '{end_date}'"
        )
        results = self.select_base_entity(columns='*', condition=condition)
        return results

    def get_max_trade_date(self):
        # 构建 SQL 查询以获取最大交易日期
        result = self.select_base_entity(columns='MAX(trade_date)', condition=None)
        return result[0][0] if result else None



from mysql_connect.common_mapper import CommonMapper

class FinancingMarginTradingMapper(CommonMapper):
    def __init__(self):
        super().__init__('financing_margin_trading')
        self.table_name = 'financing_margin_trading'

    def insert_financing_margin_trading(self, financing_margin_trading):
        trade_date = financing_margin_trading.get_trade_date()
        exchange_id = financing_margin_trading.get_exchange_id()
        trade_key = (trade_date, exchange_id)

        value = self.select_financing_margin_trading_by_trade_key(*trade_key)
        if value is not None and value:
            print(f'交易日期为{trade_date}交易所代码为{exchange_id}存在重复数据')
        else:
            self.insert_base_entity(financing_margin_trading)

    def insert_financing_margin_trading_batch(self, financing_margin_tradings):
        """
        使用数据库 UPSERT 功能批量插入

        Args:
            financing_margin_tradings: list of FinancingMarginTrading objects or single FinancingMarginTrading object
        """
        # 处理单个对象的情况
        if not isinstance(financing_margin_tradings, list):
            financing_margin_tradings = [financing_margin_tradings]

        if not financing_margin_tradings:
            return

        # 内存去重
        unique_data = {}
        duplicate_count = 0

        for financing_margin_trading in financing_margin_tradings:
            trade_date = financing_margin_trading.get_trade_date()
            exchange_id = financing_margin_trading.get_exchange_id()

            key = (trade_date, exchange_id)
            if key in unique_data:
                duplicate_count += 1
            else:
                unique_data[key] = financing_margin_trading

        valid_data = list(unique_data.values())

        if valid_data:
            # 使用 UPSERT 批量插入（需要实现 upsert 方法）
            inserted_count = self.upsert_base_entities_batch(valid_data)
            print(f'处理 {len(valid_data)} 条数据，实际插入 {inserted_count} 条新数据')

        if duplicate_count > 0:
            print(f'内存去重跳过 {duplicate_count} 条重复数据')

    # 根据交易键获取数据
    def select_financing_margin_trading_by_trade_key(self, trade_date, exchange_id):
        condition = (
            f"trade_date = '{trade_date}' AND "
            f"exchange_id = '{exchange_id}'"
        )
        result = self.select_base_entity(columns='*', condition=condition)
        return result

    def select_financing_margin_trading_by_exchange_id(self, exchange_id):
        condition = (
            f"exchange_id = '{exchange_id}'"
        )
        result = self.select_base_entity(columns='*', condition=condition)
        return result

    def select_by_date_range(self, start_date, end_date):
        condition = (
            f"trade_date >= '{start_date}' AND "
            f"trade_date <= '{end_date}'"
        )
        results = self.select_base_entity(columns='*', condition=condition)
        return results

    def get_max_trade_date(self, exchange_id):
        # 构建 SQL 查询以获取最大交易日期
        result = self.select_base_entity(columns='MAX(trade_date)', condition=None)
        return result[0][0] if result else None



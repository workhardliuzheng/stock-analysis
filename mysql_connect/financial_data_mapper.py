from mysql_connect.common_mapper import CommonMapper


class FinancialDataMapper(CommonMapper):
    def __init__(self):
        super().__init__('financial_data')
        self.table_name = 'financial_data'

    def insert_financial_data(self, financial_data):
        ts_code = financial_data.get_ts_code()
        end_date = financial_data.get_end_date()
        trade_key = (ts_code, end_date)

        value = self.select_financial_data_by_trade_key(*trade_key)
        if value is not None and value:
            print(f'编码为{ts_code}报告期为{end_date}存在重复数据')
        else:
            self.insert_base_entity(financial_data)

    def insert_financial_data_batch(self, financial_datas):
        """
        使用数据库 UPSERT 功能批量插入

        Args:
            financial_datas: list of financial_data objects or single financial_data object
        """
        # 处理单个对象的情况
        if not isinstance(financial_datas, list):
            financial_datas = [financial_datas]

        if not financial_datas:
            return

        # 内存去重
        unique_data = {}
        duplicate_count = 0

        for financial_data in financial_datas:
            ts_code = financial_data.get_ts_code()
            end_date = financial_data.get_end_date()

            key = (ts_code, end_date)
            if key in unique_data:
                duplicate_count += 1
            else:
                unique_data[key] = financial_data

        valid_data = list(unique_data.values())

        if valid_data:
            # 使用 UPSERT 批量插入（需要实现 upsert 方法）
            inserted_count = self.upsert_base_entities_batch(valid_data)
            print(f'处理 {len(valid_data)} 条数据，实际插入 {inserted_count} 条新数据')

        if duplicate_count > 0:
            print(f'内存去重跳过 {duplicate_count} 条重复数据')

    # 根据交易键获取数据
    def select_financial_data_by_trade_key(self, ts_code, end_date):
        condition = (
            f"ts_code = '{ts_code}' AND "
            f"end_date = '{end_date}'"
        )
        result = self.select_base_entity(columns='*', condition=condition)
        return result

    def select_financial_data_by_ts_code(self, ts_code):
        condition = (
            f"ts_code = '{ts_code}'"
        )
        result = self.select_base_entity(columns='*', condition=condition)
        return result

    def select_by_ts_and_dates(self, ts_code, start_date, end_date):
        condition = (
            f"ts_code = '{ts_code}' AND "
            f"end_date >= '{start_date}' AND "
            f"end_date <= '{end_date}'"
        )
        results = self.select_base_entity(columns='*', condition=condition)
        return results

    def get_max_end_date(self, ts_code):
        # 构建 SQL 查询以获取最大公告日期
        query = f"ts_code = '{ts_code}'"
        result = self.select_base_entity(columns='MAX(end_date)', condition=query)
        return result[0][0] if result else None
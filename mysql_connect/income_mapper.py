from mysql_connect.common_mapper import CommonMapper


class IncomeMapper(CommonMapper):
    def __init__(self):
        super().__init__('income')
        self.table_name = 'income'

    def insert_income(self, income):
        ts_code = income.get_ts_code()
        ann_date = income.get_ann_date()
        f_ann_date = income.get_f_ann_date()
        end_date = income.get_end_date()
        report_type = income.get_report_type()
        comp_type = income.get_comp_type()
        end_type = income.get_end_type()
        trade_key = (ts_code, ann_date, f_ann_date, end_date, report_type, comp_type, end_type)

        value = self.select_income_by_trade_key(*trade_key)
        if value is not None and value:
            print(f'编码为{ts_code}交易时间为{ann_date}存在重复数据')
        else:
            self.insert_base_entity(income)

    def insert_income_batch(self, incomes):
        """
        使用数据库 UPSERT 功能批量插入

        Args:
            incomes: list of income objects or single income object
        """
        # 处理单个对象的情况
        if not isinstance(incomes, list):
            incomes = [incomes]

        if not incomes:
            return

        # 内存去重
        unique_data = {}
        duplicate_count = 0

        for income in incomes:
            ts_code = income.get_ts_code()
            end_date = income.get_end_date()

            key = (ts_code, end_date)
            if key in unique_data:
                duplicate_count += 1
            else:
                unique_data[key] = income

        valid_data = list(unique_data.values())

        if valid_data:
            # 使用 UPSERT 批量插入（需要实现 upsert 方法）
            inserted_count = self.upsert_base_entities_batch(valid_data)
            print(f'处理 {len(valid_data)} 条数据，实际插入 {inserted_count} 条新数据')

        if duplicate_count > 0:
            print(f'内存去重跳过 {duplicate_count} 条重复数据')

    # 根据交易键获取数据
    def select_income_by_trade_key(self, ts_code, end_date):
        condition = (
            f"ts_code = '{ts_code}' AND "
            f"ann_date = '{end_date}' "
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



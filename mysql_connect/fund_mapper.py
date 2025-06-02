from mysql_connect.common_mapper import CommonMapper


class FundMapper(CommonMapper):
    def __init__(self):
        super().__init__('fund')
        self.table_name = 'fund'

    def get_name(self, ts_code):
        # 构建 SQL 查询以获取最大交易时间
        query = f" ts_code = \'{ts_code}\';"
        # 执行查询
        fund = self.select_base_entity(columns='name', condition=query)
        return fund[0][0]

    def get_found_date(self, ts_code):
        # 构建 SQL 查询以获取最大交易时间
        query = f" ts_code = \'{ts_code}\';"
        # 执行查询
        fund = self.select_base_entity(columns='found_date', condition=query)
        return fund[0][0]
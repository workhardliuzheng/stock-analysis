from mysql_connect.common_mapper import CommonMapper
from util.date_util import TimeUtils


class FundDataMapper(CommonMapper):
    def __init__(self):
        super().__init__('fund_data')
        self.table_name = 'fund_data'

    def insert_fund_data(self, fund_data):
        trade_date = fund_data.get_trade_date()
        ts_code = fund_data.get_ts_code()
        value = self.select_by_trade_date(ts_code, trade_date)
        if value is not None and value:
            print('编码为' + ts_code + '交易时间为' + TimeUtils.date_to_str(trade_date) + '存在重复数据')
        else:
            self.insert_base_entity(fund_data)

    def select_by_trade_date(self, ts_code, trade_date):
        condition = f'ts_code = \'{ts_code}\' and trade_date = \'{trade_date}\''
        market_data = self.select_base_entity(columns='*', condition=condition)
        return market_data

    def select_by_ts_code(self, ts_code=''):
        condition = f'ts_code = \'{ts_code}\''
        market_data = self.select_base_entity(columns='*', condition=condition)
        return market_data

    def select_by_code_and_trade_round(self, ts_code, start_date, end_date):

        condition = f'ts_code = \'{ts_code}\' and trade_date >= \'{start_date}\' and trade_date <= \'{end_date}\''
        data = self.select_base_entity(columns='*', condition=condition)
        return data

    def update_by_id(self, base_entity, columns):
        self.update_base_entity(base_entity, columns, ['id'])

    def get_min_trade_time(self, ts_code=''):
        # 构建 SQL 查询以获取最大交易时间
        query=''
        if ts_code:
            query = f" ts_code = \'{ts_code}\';"
        # 执行查询
        market_data = self.select_base_entity(columns='MIN(trade_date)', condition=query)
        return market_data[0][0]
from mysql_connect.common_mapper import CommonMapper


class SixtyIndexMapper(CommonMapper):
    def __init__(self):
        super().__init__('sixty_index')
        self.table_name = 'sixty_index'

    def insert_sixty_index(self, sixty_index):
        self.insert_base_entity(sixty_index)

    def select_sixty_index_by_trade_date(self, ts_code, trade_date):
        condition = f'ts_code = \'{ts_code}\' and trade_date = \'{trade_date}\''
        sixty_index = self.select_base_entity(columns='*', condition=condition)
        return sixty_index


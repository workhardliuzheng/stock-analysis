from entity.stock_basic import StockBasic
from mysql_connect.common_mapper import CommonMapper


class StockBasicMapper(CommonMapper):
    def __init__(self):
        super().__init__('stock_basic')
        self.table_name = 'stock_basic'

    def insert_stock_basic(self, stock_basic):
        """插入单条股票基础信息"""
        ts_code = stock_basic.get_ts_code()
        existing_stock = self.get_stock_basic_by_ts_code(ts_code)
        if existing_stock is not None and existing_stock:
            print(f'股票代码为 {ts_code} 的数据已存在，跳过插入')
        else:
            self.insert_base_entity(stock_basic)

    def insert_stock_basic_batch(self, stock_basic_list):
        """批量插入股票基础信息"""
        if not stock_basic_list:
            return

        try:
            # 批量插入，使用 INSERT IGNORE 避免重复插入
            self.batch_insert_base_entity(stock_basic_list)
            print(f'批量插入 {len(stock_basic_list)} 条股票基础信息成功')
        except Exception as e:
            print(f'批量插入失败: {e}，尝试逐条插入')
            # 如果批量插入失败，尝试逐条插入
            for stock_basic in stock_basic_list:
                try:
                    self.insert_stock_basic(stock_basic)
                except Exception as single_error:
                    print(f'插入股票 {stock_basic.get_ts_code()} 失败: {single_error}')

    def update_stock_basic(self, stock_basic):
        """更新股票基础信息"""
        columns = ['ts_code', 'symbol', 'name', 'area', 'industry', 'fullname',
                   'enname', 'cnspell', 'market', 'exchange', 'curr_type',
                   'list_status', 'list_date', 'delist_date', 'is_hs']
        self.update_base_entity(stock_basic, columns, ['ts_code'])

    def get_stock_basic_by_ts_code(self, ts_code):
        """根据TS代码查询股票基础信息"""
        condition = f'ts_code = \'{ts_code}\''
        stock_data = self.select_base_entity(columns='*', condition=condition)
        if stock_data and len(stock_data) > 0:
            row = stock_data[0]
            return self._convert_to_stock_basic(row)
        return None

    def get_stock_basic_by_symbol(self, symbol):
        """根据股票代码查询股票基础信息"""
        condition = f'symbol = \'{symbol}\''
        stock_data = self.select_base_entity(columns='*', condition=condition)
        if stock_data and len(stock_data) > 0:
            row = stock_data[0]
            return self._convert_to_stock_basic(row)
        return None

    def get_stocks_by_list_status(self, list_status='L'):
        """根据上市状态查询股票列表"""
        condition = f'list_status = \'{list_status}\''
        stock_data = self.select_base_entity(columns='*', condition=condition)
        return [self._convert_to_stock_basic(row) for row in stock_data] if stock_data else []

    def get_stocks_by_area(self, area):
        """根据地域查询股票列表"""
        condition = f'area = \'{area}\''
        stock_data = self.select_base_entity(columns='*', condition=condition)
        return [self._convert_to_stock_basic(row) for row in stock_data] if stock_data else []

    def get_stocks_by_industry(self, industry):
        """根据行业查询股票列表"""
        condition = f'industry = \'{industry}\''
        stock_data = self.select_base_entity(columns='*', condition=condition)
        return [self._convert_to_stock_basic(row) for row in stock_data] if stock_data else []

    def get_stocks_listed_in_date_range(self, start_date, end_date):
        """查询指定时间范围内上市的股票"""
        condition = f'list_date >= \'{start_date}\' and list_date <= \'{end_date}\' and list_status = \'L\''
        stock_data = self.select_base_entity(columns='*', condition=condition)
        return [self._convert_to_stock_basic(row) for row in stock_data] if stock_data else []

    def get_active_stocks_in_date_range(self, start_date, end_date):
        """查询指定时间范围内处于上市状态的股票（在此期间已上市且未退市）"""
        # 整个时段均上市
        condition = (f'list_date <= \'{start_date}\' and '
                     f'(delist_date >= \'{end_date}\' or delist_date is null or delist_date = \'\')')
        stock_data = self.select_base_entity(columns='*', condition=condition)
        return [self._convert_to_stock_basic(row) for row in stock_data] if stock_data else []

    def get_stocks_by_market(self, market):
        """根据市场类型查询股票列表"""
        condition = f'market = \'{market}\''
        stock_data = self.select_base_entity(columns='*', condition=condition)
        return [self._convert_to_stock_basic(row) for row in stock_data] if stock_data else []

    def get_stocks_by_exchange(self, exchange):
        """根据交易所查询股票列表"""
        condition = f'exchange = \'{exchange}\''
        stock_data = self.select_base_entity(columns='*', condition=condition)
        return [self._convert_to_stock_basic(row) for row in stock_data] if stock_data else []

    def get_hs_stocks(self, is_hs_type=None):
        """查询沪深港通标的股票"""
        if is_hs_type:
            condition = f'is_hs = \'{is_hs_type}\''
        else:
            condition = 'is_hs is not null and is_hs != \'N\' and is_hs != \'\''
        stock_data = self.select_base_entity(columns='*', condition=condition)
        return [self._convert_to_stock_basic(row) for row in stock_data] if stock_data else []

    def search_stocks_by_name(self, name_keyword):
        """根据股票名称关键字模糊查询"""
        condition = f'name like \'%{name_keyword}%\''
        stock_data = self.select_base_entity(columns='*', condition=condition)
        return [self._convert_to_stock_basic(row) for row in stock_data] if stock_data else []

    def get_all_ts_codes(self, list_status='L'):
        """获取所有股票的TS代码列表"""
        condition = f'list_status = \'{list_status}\'' if list_status else ''
        stock_data = self.select_base_entity(columns='ts_code', condition=condition)
        return [row[0] for row in stock_data] if stock_data else []

    def get_stock_count_by_status(self, list_status='L'):
        """统计指定状态的股票数量"""
        condition = f'list_status = \'{list_status}\''
        count_data = self.select_base_entity(columns='COUNT(*)', condition=condition)
        return count_data[0][0] if count_data else 0


    def get_latest_update_time(self):
        """获取最新更新时间"""
        update_data = self.select_base_entity(columns='MAX(update_time)', condition='')
        return update_data[0][0] if update_data and update_data[0][0] else None

    def _convert_to_stock_basic(self, row):
        """将数据库行数据转换为StockBasic对象"""
        if not row or len(row) < 16:
            return None

        return StockBasic(
            id=row[0],
            ts_code=row[1],
            symbol=row[2],
            name=row[3],
            area=row[4],
            industry=row[5],
            fullname=row[6],
            enname=row[7],
            cnspell=row[8],
            market=row[9],
            exchange=row[10],
            curr_type=row[11],
            list_status=row[12],
            list_date=row[13],
            delist_date=row[14],
            is_hs=row[15]
        )

    def upsert_stock_basic(self, stock_basic):
        """插入或更新股票基础信息（如果存在则更新，不存在则插入）"""
        existing_stock = self.get_stock_basic_by_ts_code(stock_basic.get_ts_code())
        if existing_stock:
            stock_basic.set_id(existing_stock.id)
            self.update_stock_basic(stock_basic)
            print(f'更新股票 {stock_basic.get_ts_code()} 的基础信息')
        else:
            self.insert_stock_basic(stock_basic)
            print(f'插入股票 {stock_basic.get_ts_code()} 的基础信息')

    def upsert_stock_basic_batch(self, stock_basic_list):
        """批量插入或更新股票基础信息"""
        if not stock_basic_list:
            return

        insert_list = []
        update_list = []

        for stock_basic in stock_basic_list:
            existing_stock = self.get_stock_basic_by_ts_code(stock_basic.get_ts_code())
            if existing_stock:
                stock_basic.set_id(existing_stock.id)
                update_list.append(stock_basic)
            else:
                insert_list.append(stock_basic)

        # 批量插入新数据
        if insert_list:
            self.insert_stock_basic_batch(insert_list)

        # 批量更新现有数据
        if update_list:
            for stock_basic in update_list:
                try:
                    self.update_stock_basic(stock_basic)
                except Exception as e:
                    print(f'更新股票 {stock_basic.get_ts_code()} 失败: {e}')

        print(f'批量处理完成：插入 {len(insert_list)} 条，更新 {len(update_list)} 条')

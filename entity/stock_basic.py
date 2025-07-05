from entity.base_entity import BaseEntity


class StockBasic(BaseEntity):
    def __init__(self, id=None, ts_code=None, symbol=None, name=None, area=None,
                 industry=None, fullname=None, enname=None, cnspell=None, market=None,
                 exchange=None, curr_type=None, list_status=None, list_date=None,
                 delist_date=None, is_hs=None):
        self.id = id
        self.ts_code = ts_code
        self.symbol = symbol
        self.name = name
        self.area = area
        self.industry = industry
        self.fullname = fullname
        self.enname = enname
        self.cnspell = cnspell
        self.market = market
        self.exchange = exchange
        self.curr_type = curr_type
        self.list_status = list_status
        self.list_date = list_date
        self.delist_date = delist_date
        self.is_hs = is_hs

    def get_ts_code(self):
        return self.ts_code

    def get_symbol(self):
        return self.symbol

    def get_name(self):
        return self.name

    def get_area(self):
        return self.area

    def get_industry(self):
        return self.industry

    def get_list_status(self):
        return self.list_status

    def get_list_date(self):
        return self.list_date

    def set_id(self, id):
        self.id = id

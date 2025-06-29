from entity.base_entity import BaseEntity


class StockWeight(BaseEntity):
    def __init__(self, id=None, index_code=None, con_code=None, trade_date=None, weight=None):
        self.id = id
        self.index_code = index_code
        self.con_code = con_code
        self.trade_date = trade_date
        self.weight = weight

    def get_index_code(self):
        return self.index_code

    def get_con_code(self):
        return self.con_code

    def get_trade_date(self):
        return self.trade_date

    def set_id(self, id):
        self.id = id
from entity.base_entity import BaseEntity

class DailyMarketData(BaseEntity):
    def __init__(self, id=None, trade_date=None, market_data=None):
        self.id = id
        self.trade_date = trade_date
        self.market_data = market_data

    # Getter methods for each field
    def get_id(self):
        return self.id

    def get_trade_date(self):
        return self.trade_date

    def get_market_data(self):
        return self.market_data

    # Setter methods for each field
    def set_id(self, id):
        self.id = id

    def set_trade_date(self, trade_date):
        self.trade_date = trade_date

    def set_market_data(self, market_data):
        self.market_data = market_data



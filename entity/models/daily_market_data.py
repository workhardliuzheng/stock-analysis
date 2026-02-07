"""
每日市场数据 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Text
from mysql_connect.db import Base


class DailyMarketData(Base):
    """每日市场汇总数据"""
    __tablename__ = 'daily_market_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(String(10), index=True)
    market_data = Column(Text)
    
    def get_id(self):
        return self.id
    
    def get_trade_date(self):
        return self.trade_date
    
    def get_market_data(self):
        return self.market_data
    
    def set_id(self, id):
        self.id = id
    
    def set_trade_date(self, trade_date):
        self.trade_date = trade_date
    
    def set_market_data(self, market_data):
        self.market_data = market_data
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def to_dict_with_backticks(self, contains_id=True):
        data_dict = self.to_dict()
        if not contains_id:
            data_dict.pop('id', None)
        return {f'`{key}`': value for key, value in sorted(data_dict.items())}

"""
市场数据 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Float
from mysql_connect.db import Base


class MarketData(Base):
    """市场整体数据"""
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(String(10), index=True)
    ts_code = Column(String(20), index=True)
    ts_name = Column(String(50))
    total_mv = Column(Float)
    amount = Column(Float)
    vol = Column(Float)
    trans_count = Column(Integer)
    pe = Column(Float)
    tr = Column(Float)
    exchange = Column(String(10))
    com_count = Column(Integer)
    total_share = Column(Float)
    float_share = Column(Float)
    float_mv = Column(Float)
    
    def get_trade_date(self):
        return self.trade_date
    
    def get_ts_code(self):
        return self.ts_code
    
    def set_id(self, id):
        self.id = id
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def to_dict_with_backticks(self, contains_id=True):
        data_dict = self.to_dict()
        if not contains_id:
            data_dict.pop('id', None)
        return {f'`{key}`': value for key, value in sorted(data_dict.items())}

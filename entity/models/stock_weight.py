"""
股票权重 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Float
from mysql_connect.db import Base


class StockWeight(Base):
    """指数成分股权重"""
    __tablename__ = 'stock_weight'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    index_code = Column(String(20), index=True)
    con_code = Column(String(20), index=True)
    trade_date = Column(String(10), index=True)
    weight = Column(Float)
    
    def get_index_code(self):
        return self.index_code
    
    def get_con_code(self):
        return self.con_code
    
    def get_trade_date(self):
        return self.trade_date
    
    def set_id(self, id):
        self.id = id
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def to_dict_with_backticks(self, contains_id=True):
        data_dict = self.to_dict()
        if not contains_id:
            data_dict.pop('id', None)
        return {f'`{key}`': value for key, value in sorted(data_dict.items())}

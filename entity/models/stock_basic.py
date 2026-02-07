"""
股票基础信息 ORM 模型
"""
from sqlalchemy import Column, Integer, String
from mysql_connect.db import Base


class StockBasic(Base):
    """股票基础信息"""
    __tablename__ = 'stock_basic'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), index=True)
    symbol = Column(String(10))
    name = Column(String(50))
    area = Column(String(20))
    industry = Column(String(50))
    fullname = Column(String(100))
    enname = Column(String(100))
    cnspell = Column(String(50))
    market = Column(String(20))
    exchange = Column(String(10))
    curr_type = Column(String(10))
    list_status = Column(String(5))
    list_date = Column(String(10))
    delist_date = Column(String(10))
    is_hs = Column(String(5))
    
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
    
    def get_delist_date(self):
        return self.delist_date
    
    def set_id(self, id):
        self.id = id
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def to_dict_with_backticks(self, contains_id=True):
        data_dict = self.to_dict()
        if not contains_id:
            data_dict.pop('id', None)
        return {f'`{key}`': value for key, value in sorted(data_dict.items())}

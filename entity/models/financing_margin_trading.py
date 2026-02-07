"""
融资融券数据 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Float
from mysql_connect.db import Base


class FinancingMarginTrading(Base):
    """融资融券交易数据"""
    __tablename__ = 'financing_margin_trading'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(String(10), index=True)
    exchange_id = Column(String(10), index=True)
    rzye = Column(Float)
    rzmre = Column(Float)
    rzche = Column(Float)
    rqye = Column(Float)
    rqmcl = Column(Float)
    rzrqye = Column(Float)
    rqyl = Column(Float)
    
    def get_id(self):
        return self.id
    
    def get_trade_date(self):
        return self.trade_date
    
    def get_exchange_id(self):
        return self.exchange_id
    
    def get_rzye(self):
        return self.rzye
    
    def get_rzmre(self):
        return self.rzmre
    
    def get_rzche(self):
        return self.rzche
    
    def get_rqye(self):
        return self.rqye
    
    def get_rqmcl(self):
        return self.rqmcl
    
    def get_rzrqye(self):
        return self.rzrqye
    
    def get_rqyl(self):
        return self.rqyl
    
    def set_id(self, id):
        self.id = id
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def to_dict_with_backticks(self, contains_id=True):
        data_dict = self.to_dict()
        if not contains_id:
            data_dict.pop('id', None)
        return {f'`{key}`': value for key, value in sorted(data_dict.items())}

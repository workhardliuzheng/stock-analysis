"""
股票每日基本面 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Float
from mysql_connect.db import Base


class StockDailyBasic(Base):
    """股票每日基本面数据"""
    __tablename__ = 'stock_daily_basic'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), index=True)
    trade_date = Column(String(10), index=True)
    close = Column(Float)
    turnover_rate = Column(Float)
    turnover_rate_f = Column(Float)
    volume_ratio = Column(Float)
    pe = Column(Float)
    pe_ttm = Column(Float)
    pb = Column(Float)
    ps = Column(Float)
    ps_ttm = Column(Float)
    dv_ratio = Column(Float)
    dv_ttm = Column(Float)
    total_share = Column(Float)
    float_share = Column(Float)
    free_share = Column(Float)
    total_mv = Column(Float)
    circ_mv = Column(Float)
    pe_profit_dedt = Column(Float)
    pe_ttm_profit_dedt = Column(Float)
    
    def get_id(self):
        return self.id
    
    def get_ts_code(self):
        return self.ts_code
    
    def get_trade_date(self):
        return self.trade_date
    
    def get_close(self):
        return self.close
    
    def get_pe(self):
        return self.pe
    
    def get_pe_ttm(self):
        return self.pe_ttm
    
    def get_pb(self):
        return self.pb
    
    def get_total_mv(self):
        return self.total_mv
    
    def get_circ_mv(self):
        return self.circ_mv
    
    def get_pe_profit_dedt(self):
        return self.pe_profit_dedt
    
    def get_pe_ttm_profit_dedt(self):
        return self.pe_ttm_profit_dedt
    
    def set_id(self, id):
        self.id = id
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def to_dict_with_backticks(self, contains_id=True):
        data_dict = self.to_dict()
        if not contains_id:
            data_dict.pop('id', None)
        return {f'`{key}`': value for key, value in sorted(data_dict.items())}

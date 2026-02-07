"""
基金数据 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Float
from mysql_connect.db import Base


class FundData(Base):
    """基金/ETF 行情数据"""
    __tablename__ = 'fund_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), index=True)
    trade_date = Column(String(10), index=True)
    name = Column(String(50))
    pre_close = Column(Float)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    change = Column(Float)
    pct_chg = Column(Float)
    vol = Column(Float)
    amount = Column(Float)
    m5 = Column(Float)
    m10 = Column(Float)
    m20 = Column(Float)
    m60 = Column(Float)
    m120 = Column(Float)
    
    def get_trade_date(self):
        return self.trade_date
    
    def get_ts_code(self):
        return self.ts_code
    
    def set_id(self, id):
        self.id = id
    
    @staticmethod
    def df_to_entity(row):
        return FundData(
            id=row.get('id'),
            ts_code=row.get('ts_code'),
            trade_date=row.get('trade_date'),
            name=row.get('name'),
            pre_close=row.get('pre_close'),
            open=row.get('open'),
            high=row.get('high'),
            low=row.get('low'),
            close=row.get('close'),
            change=row.get('change'),
            pct_chg=row.get('pct_chg'),
            vol=row.get('vol'),
            amount=row.get('amount'),
            m5=row.get('m5'),
            m10=row.get('m10'),
            m20=row.get('m20'),
            m60=row.get('m60'),
            m120=row.get('m120')
        )
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def to_dict_with_backticks(self, contains_id=True):
        data_dict = self.to_dict()
        if not contains_id:
            data_dict.pop('id', None)
        return {f'`{key}`': value for key, value in sorted(data_dict.items())}

"""
股票行情数据 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Float, Text
from mysql_connect.db import Base


class StockData(Base):
    """股票行情数据（含技术指标）"""
    __tablename__ = 'stock_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), index=True)
    trade_date = Column(String(10), index=True)
    close = Column(Float)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    pre_close = Column(Float)
    change = Column(Float)
    pct_chg = Column(Float)
    vol = Column(Float)
    amount = Column(Float)
    average_date = Column(Float)
    average_amount = Column(Float)
    deviation_rate = Column(Text)
    name = Column(String(50))
    pe_weight = Column(Float)
    pe_ttm_weight = Column(Float)
    pb_weight = Column(Float)
    pe = Column(Float)
    pb = Column(Float)
    pe_ttm = Column(Float)
    pe_profit_dedt = Column(Float)
    pe_profit_dedt_ttm = Column(Float)
    ma_5 = Column(Float)
    ma_10 = Column(Float)
    ma_20 = Column(Float)
    ma_50 = Column(Float)
    wma_5 = Column(Float)
    wma_10 = Column(Float)
    wma_20 = Column(Float)
    wma_50 = Column(Float)
    macd = Column(Float)
    macd_signal_line = Column(Float)
    macd_histogram = Column(Float)
    rsi = Column(Float)
    kdj_k = Column(Float)
    kdj_d = Column(Float)
    kdj_j = Column(Float)
    bb_high = Column(Float)
    bb_mid = Column(Float)
    bb_low = Column(Float)
    obv = Column(Float)
    cross_signals = Column(Text)
    percentile_ranks = Column(Text)
    
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

"""
持仓状态 ORM 模型

记录每日每指数持仓状态（成本、市值、权重、信号、操作）
"""
from sqlalchemy import Column, Integer, String, Date, DateTime, DECIMAL, func
from mysql_connect.db import Base


class PortfolioState(Base):
    """每日持仓状态"""
    __tablename__ = 'portfolio_state'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, index=True)
    ts_code = Column(String(20), nullable=False, index=True)
    name = Column(String(50))

    # --- 价值维度 ---
    cost_basis = Column(DECIMAL(14, 2), default=0.00)       # 成本(原值)
    market_value = Column(DECIMAL(14, 2), default=0.00)      # 市值(现值)
    weight_pct = Column(DECIMAL(10, 4), default=0.0000)      # 权重(%)
    return_pct = Column(DECIMAL(10, 4), default=0.0000)      # 收益率(%)

    # --- 信号维度 ---
    current_signal = Column(String(10))                       # BUY/SELL/HOLD
    signal_strength = Column(DECIMAL(10, 4), default=0.0000)  # 信号强度
    confidence = Column(DECIMAL(10, 4), default=0.0000)       # 置信度
    factor_score = Column(DECIMAL(10, 4), default=0.0000)     # 多因子评分

    # --- 操作维度 ---
    action = Column(String(20))                                # 建仓/加仓/减仓/清仓/持有
    action_value = Column(DECIMAL(14, 2), default=0.00)       # 操作金额(元)
    new_market_value = Column(DECIMAL(14, 2), default=0.00)   # 操作后市值
    new_weight_pct = Column(DECIMAL(10, 4), default=0.0000)   # 操作后权重

    # --- 汇总 ---
    total_position_pct = Column(DECIMAL(10, 4), default=0.0000)  # 总仓位(%)
    total_market_value = Column(DECIMAL(16, 2), default=0.00)    # 总市值(元)
    cash_pct = Column(DECIMAL(10, 4), default=0.0000)            # 现金比例(%)

    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

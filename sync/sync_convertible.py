"""
可转债数据同步模块

负责从 Tushare 获取可转债基本信息(cb_basic)和日线行情(cb_daily)，
自动创建数据库表并同步数据。

用法:
    from sync.sync_convertible import sync_all, sync_basic, sync_daily

    sync_all()              # 同步全部
    sync_daily()            # 仅同步日线（增量）
    sync_daily(ts_code='113044.SH')  # 仅同步指定转债

CLI:
    python sync/sync_convertible.py basic      # 同步基本信息
    python sync/sync_convertible.py daily      # 同步日线
    python sync/sync_convertible.py summary    # 查看概要
"""

import pandas as pd
import time
from datetime import datetime, timedelta
from sqlalchemy import text, Column, Integer, String, DECIMAL, DateTime, func, UniqueConstraint, Index
from mysql_connect.db import get_session, get_engine, Base
from mysql_connect.common_mapper import CommonMapper
from entity.convertible_bond import ConvertibleBondBasic, ConvertibleBondDaily
from tu_share_factory.tu_share_factory import TuShareFactory

# ==================== ORM 模型（用于自动建表） ====================


class CbBasicOrm(Base):
    """可转债基本信息 ORM"""
    __tablename__ = 'cb_basic'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), unique=True, nullable=False, comment='转债代码')
    bond_short_name = Column(String(50), comment='转债简称')
    stk_code = Column(String(20), comment='正股代码')
    stk_short_name = Column(String(50), comment='正股简称')
    value_date = Column(String(10), comment='起息日期')
    maturity_date = Column(String(10), comment='到期日期')
    issue_size = Column(DECIMAL(20, 2), comment='发行规模(元)')
    remain_size = Column(DECIMAL(20, 2), comment='剩余规模(元)')
    conv_start_date = Column(String(10), comment='转股开始日')
    conv_end_date = Column(String(10), comment='转股结束日')
    conv_price = Column(DECIMAL(10, 4), comment='转股价')
    list_date = Column(String(10), comment='上市日期')
    delist_date = Column(String(10), comment='退市日期')
    exchange = Column(String(10), comment='交易所')
    rate_type = Column(String(10), comment='利率类型')
    coupon_rate = Column(DECIMAL(10, 4), comment='票面利率')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(),
                        onupdate=func.now(), comment='更新时间')


class CbDailyOrm(Base):
    """可转债日线行情 ORM"""
    __tablename__ = 'cb_daily'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False, index=True, comment='转债代码')
    trade_date = Column(String(10), nullable=False, index=True, comment='交易日期')
    open = Column(DECIMAL(10, 3), comment='开盘价')
    high = Column(DECIMAL(10, 3), comment='最高价')
    low = Column(DECIMAL(10, 3), comment='最低价')
    close = Column(DECIMAL(10, 3), comment='收盘价')
    pre_close = Column(DECIMAL(10, 3), comment='昨收盘价')
    change = Column(DECIMAL(10, 3), comment='涨跌额')
    pct_chg = Column(DECIMAL(10, 4), comment='涨跌幅(%)')
    vol = Column(DECIMAL(20, 2), comment='成交量(手)')
    amount = Column(DECIMAL(20, 2), comment='成交额(元)')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(),
                        onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        UniqueConstraint('ts_code', 'trade_date', name='uk_cb_daily_ts_date'),
        Index('idx_cb_daily_ts_code', 'ts_code'),
        Index('idx_cb_daily_trade_date', 'trade_date'),
    )

# ==================== 常量 ====================

CB_BASIC_FIELDS = [
    'ts_code', 'bond_short_name', 'stk_code', 'stk_short_name',
    'value_date', 'maturity_date', 'issue_size', 'remain_size',
    'conv_start_date', 'conv_end_date', 'conv_price',
    'list_date', 'delist_date', 'exchange', 'rate_type', 'coupon_rate',
]

CB_DAILY_FIELDS = [
    'ts_code', 'trade_date', 'open', 'high', 'low', 'close',
    'pre_close', 'change', 'pct_chg', 'vol', 'amount',
]

BATCH_SIZE = 500
DAYS_PER_REQUEST = 60  # Tushare 单次请求最大天数限制


# ==================== 数据库初始化 ====================


def init_tables():
    """
    创建 cb_basic 和 cb_daily 表（如不存在）
    显式指定 utf8mb4 字符集以支持中文
    """
    engine = get_engine()
    Base.metadata.create_all(engine, tables=[CbBasicOrm.__table__, CbDailyOrm.__table__])

    # 确保字符集为 utf8mb4（首次建表后设置）
    with get_session() as session:
        for tbl in ['cb_basic', 'cb_daily']:
            session.execute(
                text(f"ALTER TABLE {tbl} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            )

    print("[OK] 可转债数据表已就绪")


def get_latest_trade_date() -> str:
    """获取 cb_daily 表中已有数据的最大交易日期"""
    with get_session() as session:
        result = session.execute(
            text("SELECT MAX(trade_date) FROM cb_daily")
        ).scalar()
    return result or ''


def get_active_basic_codes() -> list:
    """
    获取所有在库的基本信息中的转债代码
    （用于增量同步日线时确定哪些转债需要更新）
    """
    with get_session() as session:
        result = session.execute(
            text("SELECT ts_code FROM cb_basic WHERE delist_date IS NULL")
        ).fetchall()
    return [r[0] for r in result]


# ==================== 数据同步 ====================


def sync_basic() -> int:
    """
    同步可转债基本信息 (cb_basic)

    Returns:
        int: 同步/更新条数
    """
    pro = TuShareFactory.build_api_client()
    mapper = CommonMapper('cb_basic')

    print("[CB] 正在获取可转债基本信息...")
    df = pro.cb_basic(fields=','.join(CB_BASIC_FIELDS))

    if df is None or df.empty:
        print("[WARN] 未获取到可转债基本信息")
        return 0

    print(f"[CB] 获取到 {len(df)} 条可转债基本信息，正在落库...")

    entities = []
    for _, row in df.iterrows():
        entity = ConvertibleBondBasic.from_df_row(row)
        entities.append(entity)

        if len(entities) >= BATCH_SIZE:
            mapper.upsert_base_entities_batch(entities)
            print(f"[CB] 已同步 {len(entities)} 条...")
            entities = []

    if entities:
        mapper.upsert_base_entities_batch(entities)

    total = len(df)
    print(f"[OK] 可转债基本信息同步完成，共 {total} 条")
    return total


def _get_stock_close(pro, stk_code: str, trade_date: str) -> float:
    """
    获取指定股票在指定日期的收盘价

    Args:
        pro: Tushare API client
        stk_code: 正股代码
        trade_date: 交易日期

    Returns:
        float: 收盘价，获取失败返回 None
    """
    try:
        df = pro.daily(ts_code=stk_code, trade_date=trade_date,
                       fields='close', limit=1)
        if df is not None and not df.empty:
            return float(df.iloc[0]['close'])
    except Exception:
        pass
    return None


def sync_daily(start: str = None, end: str = None, ts_code: str = None) -> int:
    """
    同步可转债日线行情 (cb_daily)

    Args:
        start: 开始日期 YYYYMMDD，默认从最新数据后一天开始
        end: 结束日期 YYYYMMDD，默认为今天
        ts_code: 指定转债代码，不传则同步全部（但分批请求，避免超限）

    Returns:
        int: 同步条数
    """
    pro = TuShareFactory.build_api_client()
    mapper = CommonMapper('cb_daily')

    today = datetime.now().strftime('%Y%m%d')

    # 确定开始日期
    if start is None:
        latest = get_latest_trade_date()
        if latest:
            # 从最新日期的下一天开始
            dt = datetime.strptime(latest, '%Y%m%d') + timedelta(days=1)
            start = dt.strftime('%Y%m%d')
        else:
            # 首次同步：获取近1年数据
            dt = datetime.now() - timedelta(days=365)
            start = dt.strftime('%Y%m%d')

    if end is None:
        end = today

    if start >= end:
        print(f"[CB] 日线数据已是最新 (latest={get_latest_trade_date()})")
        return 0

    print(f"[CB] 同步可转债日线: {start} ~ {end}")

    total = 0
    codes_to_sync = []

    if ts_code:
        codes_to_sync = [ts_code]
    else:
        codes_to_sync = get_active_basic_codes()
        if not codes_to_sync:
            # 如果基本信息还没同步，先同步基本信息
            print("[WARN] cb_basic 为空，先同步基本信息...")
            sync_basic()
            codes_to_sync = get_active_basic_codes()

    if not codes_to_sync:
        print("[WARN] 没有需要同步日线的转债代码")
        return 0

    print(f"[CB] 待同步转债数: {len(codes_to_sync)}")

    # 逐只同步，控制请求速度避免限流
    entities = []
    for idx, code in enumerate(codes_to_sync):
        try:
            # 每只转债之间延时 0.35s，控制 ~170次/分钟 < 200次/分钟限制
            if idx > 0:
                time.sleep(0.35)

            df = pro.cb_daily(ts_code=code, start_date=start,
                              end_date=end,
                              fields=','.join(CB_DAILY_FIELDS))

            if df is None or df.empty:
                continue

            for _, row in df.iterrows():
                entity = ConvertibleBondDaily.from_df_row(row)
                entities.append(entity)

            if len(entities) >= BATCH_SIZE:
                mapper.upsert_base_entities_batch(entities)
                total += len(entities)
                print(f"[CB] 已同步 {total} 条日线...")
                entities = []

        except Exception as e:
            err_msg = str(e)
            if '频率超限' in err_msg or 'rate limit' in err_msg.lower():
                print(f"[WARN] 触发限流，等待60秒后重试 {code}...")
                time.sleep(60)
                try:
                    df = pro.cb_daily(ts_code=code, start_date=start,
                                      end_date=end,
                                      fields=','.join(CB_DAILY_FIELDS))
                    if df is not None and not df.empty:
                        for _, row in df.iterrows():
                            entity = ConvertibleBondDaily.from_df_row(row)
                            entities.append(entity)
                        if len(entities) >= BATCH_SIZE:
                            mapper.upsert_base_entities_batch(entities)
                            total += len(entities)
                            entities = []
                except Exception as e2:
                    print(f"[WARN] 重试 {code} 仍失败: {e2}")
            else:
                print(f"[WARN] 同步 {code} 日线失败: {err_msg[:80]}")
            continue

    # 落库剩余
        if entities:
            mapper.upsert_base_entities_batch(entities)
            total += len(entities)
            print(f"[CB] 已同步 {total} 条日线...")

    print(f"[OK] 可转债日线同步完成，共 {total} 条")
    return total


def sync_all():
    """
    全量同步: 基本信息 + 日线行情
    """
    init_tables()

    n_basic = sync_basic()
    n_daily = sync_daily()

    print(f"\n[CB] ======== 可转债数据同步完成 ========")
    print(f"[CB] 基本信息: {n_basic} 条")
    print(f"[CB] 日线行情: {n_daily} 条")


# ==================== 简易数据查看 ====================


def show_summary():
    """打印可转债数据概要"""
    from mysql_connect.db import get_session

    with get_session() as session:
        basic_count = session.execute(
            text("SELECT COUNT(*) FROM cb_basic")
        ).scalar() or 0
        daily_count = session.execute(
            text("SELECT COUNT(*) FROM cb_daily")
        ).scalar() or 0
        daily_dates = session.execute(
            text("SELECT MIN(trade_date), MAX(trade_date) FROM cb_daily")
        ).fetchone()
        active_bonds = session.execute(
            text("SELECT COUNT(*) FROM cb_basic WHERE delist_date IS NULL")
        ).scalar() or 0

    print(f"  基本信息: {basic_count} 只")
    print(f"  日线行情: {daily_count} 条")
    print(f"  日线日期: {daily_dates[0] or 'N/A'} ~ {daily_dates[1] or 'N/A'}")
    print(f"  仍在交易的: {active_bonds} 只")


# ==================== CLI ====================

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'basic':
            init_tables()
            sync_basic()
        elif cmd == 'daily':
            init_tables()
            start = sys.argv[2] if len(sys.argv) > 2 else None
            end = sys.argv[3] if len(sys.argv) > 3 else None
            sync_daily(start=start, end=end)
        elif cmd == 'summary':
            show_summary()
        else:
            print(f"未知命令: {cmd}")
            print("用法: python sync/sync_convertible.py [basic|daily|summary|all]")
    else:
        init_tables()
        sync_all()
        show_summary()

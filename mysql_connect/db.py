"""
数据库基础设施模块

提供 SQLAlchemy 连接池和会话管理
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
import yaml
from entity import constant

# ORM 基类 - 所有实体模型继承此类
Base = declarative_base()

# 全局单例
_engine = None
_SessionFactory = None


def get_engine():
    """获取数据库引擎（单例，带连接池）"""
    global _engine
    if _engine is None:
        with open(constant.CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)['database']
        
        url = f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}/{config['database']}?charset=utf8mb4"
        _engine = create_engine(
            url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
    return _engine


def get_session_factory():
    """获取会话工厂（单例）"""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine())
    return _SessionFactory


@contextmanager
def get_session():
    """
    获取数据库会话（上下文管理器）
    
    自动管理事务：
    - 正常退出时自动 commit
    - 异常时自动 rollback
    - 最后自动关闭会话
    
    使用示例:
        with get_session() as session:
            session.add(entity)
            # 自动提交
    """
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_pool_status():
    """获取连接池状态（用于监控）"""
    engine = get_engine()
    pool = engine.pool
    return {
        'size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow()
    }

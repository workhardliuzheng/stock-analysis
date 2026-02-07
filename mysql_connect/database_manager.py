"""
数据库管理器（向后兼容适配器）

保留原有接口，内部使用 SQLAlchemy 会话管理
"""
import numpy as np
from sqlalchemy import text

from mysql_connect.db import get_session, get_engine, get_pool_status


def nan_to_null(value):
    """将 NaN 值转换为 None"""
    try:
        if value is None:
            return None
        if isinstance(value, float) and np.isnan(value):
            return None
        return value
    except (TypeError, ValueError):
        return value


class DatabaseManager:
    """
    数据库管理器
    
    向后兼容的适配器，保留原有接口签名，
    内部使用 SQLAlchemy 连接池和会话管理。
    
    注意：connect() 和 disconnect() 现在是空操作，
    连接由连接池自动管理。
    """
    
    def __init__(self):
        # 触发引擎初始化（如果尚未初始化）
        get_engine()
        self.connection = None  # 保留属性以兼容旧代码
    
    def connect(self):
        """连接数据库（空操作，由连接池管理）"""
        pass
    
    def disconnect(self):
        """断开连接（空操作，由连接池管理）"""
        pass
    
    def rollback(self):
        """回滚事务（空操作，由会话管理器自动处理）"""
        pass
    
    def insert(self, table, data):
        """插入单条记录"""
        # 处理带反引号的键名
        clean_data = {k.strip('`'): nan_to_null(v) for k, v in data.items()}
        
        columns = ', '.join([f'`{k}`' for k in clean_data.keys()])
        placeholders = ', '.join([f':{k}' for k in clean_data.keys()])
        sql = f"INSERT INTO `{table}` ({columns}) VALUES ({placeholders})"
        
        with get_session() as session:
            session.execute(text(sql), clean_data)
    
    def delete(self, table, condition):
        """删除记录"""
        sql = f"DELETE FROM `{table}` WHERE {condition}"
        
        with get_session() as session:
            session.execute(text(sql))
    
    def update(self, table, data, condition):
        """更新记录"""
        clean_data = {k.strip('`'): nan_to_null(v) for k, v in data.items()}
        set_clause = ', '.join([f'`{k}` = :{k}' for k in clean_data.keys()])
        sql = f"UPDATE `{table}` SET {set_clause} WHERE {condition}"
        
        with get_session() as session:
            session.execute(text(sql), clean_data)
    
    def select(self, table, columns='*', condition=None):
        """查询记录"""
        sql = f"SELECT {columns} FROM `{table}`"
        if condition:
            sql += f" WHERE {condition}"
        
        with get_session() as session:
            result = session.execute(text(sql))
            return result.fetchall()
    
    def execute_sql(self, sql):
        """执行原始 SQL"""
        with get_session() as session:
            result = session.execute(text(sql))
            try:
                return result.fetchall()
            except Exception:
                return None
    
    def batch_insert(self, table, entities):
        """批量插入"""
        if not entities:
            return
        
        sample_data = entities[0].to_dict_with_backticks()
        clean_keys = [k.strip('`') for k in sample_data.keys()]
        
        columns = ', '.join([f'`{k}`' for k in clean_keys])
        placeholders = ', '.join([f':{k}' for k in clean_keys])
        sql = f"INSERT INTO `{table}` ({columns}) VALUES ({placeholders})"
        
        with get_session() as session:
            for entity in entities:
                entity_dict = entity.to_dict_with_backticks()
                clean_data = {k.strip('`'): nan_to_null(v) for k, v in entity_dict.items()}
                session.execute(text(sql), clean_data)
    
    def upsert_base_entities_batch(self, table, entities):
        """
        批量 UPSERT 实现
        
        Args:
            table: 表名
            entities: 实体列表
        Returns:
            int: 影响的行数
        """
        if not entities:
            return 0
        
        first_entity = entities[0]
        sample_dict = first_entity.to_dict_with_backticks(contains_id=True)
        clean_keys = [k.strip('`') for k in sample_dict.keys()]
        
        columns = ', '.join([f'`{k}`' for k in clean_keys])
        placeholders = ', '.join([f':{k}' for k in clean_keys])
        update_clause = ', '.join([f'`{k}` = VALUES(`{k}`)' for k in clean_keys if k != 'id'])
        
        sql = f"""
            INSERT INTO `{table}` ({columns})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_clause}
        """
        
        affected_rows = 0
        with get_session() as session:
            for entity in entities:
                entity_dict = entity.to_dict_with_backticks(contains_id=True)
                clean_data = {k.strip('`'): nan_to_null(v) for k, v in entity_dict.items()}
                result = session.execute(text(sql), clean_data)
                affected_rows += result.rowcount
        
        return affected_rows
    
    def get_pool_status(self):
        """获取连接池状态"""
        return get_pool_status()

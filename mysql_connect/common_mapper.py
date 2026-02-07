"""
通用 Mapper 基类

提供基础的 CRUD 操作，使用 SQLAlchemy 会话管理
"""
import numpy as np
from sqlalchemy import text

from mysql_connect.db import get_session


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


class CommonMapper:
    """通用 Mapper 基类"""
    
    def __init__(self, table_name):
        self.table_name = table_name
    
    def insert_base_entity(self, base_entity):
        """插入单个实体"""
        data = base_entity.to_dict_with_backticks(contains_id=False)
        # 移除反引号用于参数化查询
        clean_data = {k.strip('`'): nan_to_null(v) for k, v in data.items()}
        
        columns = ', '.join([f'`{k}`' for k in clean_data.keys()])
        placeholders = ', '.join([f':{k}' for k in clean_data.keys()])
        sql = f"INSERT INTO `{self.table_name}` ({columns}) VALUES ({placeholders})"
        
        with get_session() as session:
            session.execute(text(sql), clean_data)
    
    def batch_insert_base_entity(self, base_entity_list):
        """批量插入实体"""
        if not base_entity_list:
            return
        
        sample = base_entity_list[0].to_dict_with_backticks(contains_id=False)
        clean_keys = [k.strip('`') for k in sample.keys()]
        
        columns = ', '.join([f'`{k}`' for k in clean_keys])
        placeholders = ', '.join([f':{k}' for k in clean_keys])
        sql = f"INSERT INTO `{self.table_name}` ({columns}) VALUES ({placeholders})"
        
        batch_data = []
        for entity in base_entity_list:
            entity_dict = entity.to_dict_with_backticks(contains_id=False)
            clean_data = {k.strip('`'): nan_to_null(v) for k, v in entity_dict.items()}
            batch_data.append(clean_data)
        
        with get_session() as session:
            for data in batch_data:
                session.execute(text(sql), data)
    
    def upsert_base_entities_batch(self, base_entity_list):
        """批量插入或更新实体（UPSERT）"""
        if not base_entity_list:
            return 0
        
        sample = base_entity_list[0].to_dict_with_backticks(contains_id=True)
        clean_keys = [k.strip('`') for k in sample.keys()]
        
        columns = ', '.join([f'`{k}`' for k in clean_keys])
        placeholders = ', '.join([f':{k}' for k in clean_keys])
        update_clause = ', '.join([f'`{k}` = VALUES(`{k}`)' for k in clean_keys if k != 'id'])
        
        sql = f"""
            INSERT INTO `{self.table_name}` ({columns})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_clause}
        """
        
        batch_data = []
        for entity in base_entity_list:
            entity_dict = entity.to_dict_with_backticks(contains_id=True)
            clean_data = {k.strip('`'): nan_to_null(v) for k, v in entity_dict.items()}
            batch_data.append(clean_data)
        
        affected_rows = 0
        with get_session() as session:
            for data in batch_data:
                result = session.execute(text(sql), data)
                affected_rows += result.rowcount
        
        return affected_rows
    
    def select_base_entity(self, columns, condition):
        """查询实体"""
        sql = f"SELECT {columns} FROM `{self.table_name}`"
        if condition:
            sql += f" WHERE {condition}"
        
        with get_session() as session:
            result = session.execute(text(sql))
            return result.fetchall()
    
    def delete_by_condition(self, condition):
        """根据条件删除"""
        sql = f"DELETE FROM `{self.table_name}` WHERE {condition}"
        
        with get_session() as session:
            session.execute(text(sql))
    
    def update_base_entity(self, base_entity, columns, condition_columns):
        """更新实体"""
        entity_dict = base_entity.to_dict()
        extracted_data = {}
        condition_parts = []
        
        for key in entity_dict.keys():
            if key in columns:
                extracted_data[key] = nan_to_null(entity_dict[key])
            
            if key in condition_columns:
                value = entity_dict[key]
                if isinstance(value, str):
                    value = f"'{value}'"
                condition_parts.append(f"`{key}`={value}")
        
        condition_string = " AND ".join(condition_parts)
        set_clause = ', '.join([f'`{k}` = :{k}' for k in extracted_data.keys()])
        sql = f"UPDATE `{self.table_name}` SET {set_clause} WHERE {condition_string}"
        
        with get_session() as session:
            session.execute(text(sql), extracted_data)
    
    def execute_sql(self, sql):
        """执行原始 SQL"""
        with get_session() as session:
            result = session.execute(text(sql))
            try:
                return result.fetchall()
            except Exception:
                return None

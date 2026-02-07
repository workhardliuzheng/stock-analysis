import pandas as pd
import numpy as np

# Entity参数缓存，避免重复反射
_ENTITY_PARAMS_CACHE = {}


class ClassUtil:
    @staticmethod
    def create_entities_from_data(entity_class, data):
        # 获取实体类的所有属性名称
        entity_attributes = entity_class.__init__.__code__.co_varnames[1:]  # 去掉 'self'

        # 创建字典，将数据按属性名称映射
        kwargs = dict(zip(entity_attributes, data))

        # 使用 **kwargs 创建实体对象
        entity = entity_class(**kwargs)
        return entity

    @staticmethod
    def is_null_value(value) -> bool:
        """
        统一判断空值（NaN、None、pd.NA、空字符串）
        
        Args:
            value: 待检查的值
            
        Returns:
            bool: 是否为空值
        """
        if value is None:
            return True
        if isinstance(value, str) and value == '':
            return True
        try:
            if isinstance(value, float) and np.isnan(value):
                return True
        except (TypeError, ValueError):
            pass
        try:
            if pd.isna(value):
                return True
        except (TypeError, ValueError):
            pass
        return False

    @staticmethod
    def from_dataframe_row(entity_class, row, field_mapping=None):
        """
        从DataFrame行创建Entity对象，自动处理空值
        
        Args:
            entity_class: Entity类
            row: DataFrame的一行（Series或dict）
            field_mapping: 字段映射 {df列名: entity参数名}，如 {'open': 'open_price'}
            
        Returns:
            Entity实例
        """
        # 获取Entity的__init__参数（使用缓存）
        if entity_class not in _ENTITY_PARAMS_CACHE:
            params = entity_class.__init__.__code__.co_varnames[1:]  # 排除self
            _ENTITY_PARAMS_CACHE[entity_class] = params
        params = _ENTITY_PARAMS_CACHE[entity_class]
        
        # 转换row为dict
        if hasattr(row, 'to_dict'):
            row_dict = row.to_dict()
        else:
            row_dict = dict(row)
        
        # 应用字段映射（反向：entity参数名 -> df列名）
        reverse_mapping = {}
        if field_mapping:
            reverse_mapping = {v: k for k, v in field_mapping.items()}
        
        # 构建kwargs
        kwargs = {}
        for param in params:
            # 确定从哪个列名获取值
            col_name = reverse_mapping.get(param, param)
            
            if col_name in row_dict:
                value = row_dict[col_name]
                kwargs[param] = None if ClassUtil.is_null_value(value) else value
            else:
                kwargs[param] = None
        
        return entity_class(**kwargs)

    @staticmethod
    def from_dataframe(entity_class, df, field_mapping=None) -> list:
        """
        批量从DataFrame创建Entity对象列表
        
        Args:
            entity_class: Entity类
            df: DataFrame
            field_mapping: 字段映射 {df列名: entity参数名}
            
        Returns:
            Entity实例列表
        """
        entities = []
        for _, row in df.iterrows():
            entity = ClassUtil.from_dataframe_row(entity_class, row, field_mapping)
            entities.append(entity)
        return entities
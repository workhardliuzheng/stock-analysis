import pandas as pd
import numpy as np

# Entity参数缓存，避免重复反射
_ENTITY_PARAMS_CACHE = {}


class ClassUtil:
    @staticmethod
    def create_entities_from_data(entity_class, data):
        """
        从数据库查询结果创建实体对象
        
        Args:
            entity_class: 实体类
            data: 数据库返回的 Row 对象（支持 _mapping 属性）或元组
        
        Returns:
            Entity 实例
        """
        # 获取实体类的所有属性名称
        entity_attributes = entity_class.__init__.__code__.co_varnames[1:]  # 去掉 'self'

        # 检查数据是否有 _mapping 属性（SQLAlchemy Row 对象）
        if hasattr(data, '_mapping'):
            # 使用列名映射（更安全）
            data_dict = dict(data._mapping)
            kwargs = {}
            for attr in entity_attributes:
                if attr in data_dict:
                    kwargs[attr] = data_dict[attr]
                else:
                    kwargs[attr] = None
        else:
            # 兼容旧的位置映射方式
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
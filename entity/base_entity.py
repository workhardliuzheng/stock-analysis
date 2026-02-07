from abc import abstractmethod

from util.class_util import ClassUtil


class BaseEntity:

    def to_dict(self):
        return {key: value for key, value in self.__dict__.items()}

    def to_dict_with_backticks(self, contains_id=True):
        data_dict = self.to_dict()
        if not contains_id:  # 简化条件判断
            data_dict.pop('id', None)

        # 按键名排序保证顺序一致
        return {f'`{key}`': value for key, value in sorted(data_dict.items())}

    def columns(self):
        return self.__dict__.values()

    @abstractmethod
    def from_list_to_entity(self, list):
        pass

    @classmethod
    def from_df_row(cls, row, field_mapping=None):
        """
        从DataFrame行创建实例
        
        Args:
            row: DataFrame的一行（Series或dict）
            field_mapping: 字段映射 {df列名: entity参数名}
            
        Returns:
            Entity实例
        """
        return ClassUtil.from_dataframe_row(cls, row, field_mapping)

    @classmethod
    def from_df(cls, df, field_mapping=None) -> list:
        """
        批量从DataFrame创建实例列表
        
        Args:
            df: DataFrame
            field_mapping: 字段映射 {df列名: entity参数名}
            
        Returns:
            Entity实例列表
        """
        return ClassUtil.from_dataframe(cls, df, field_mapping)
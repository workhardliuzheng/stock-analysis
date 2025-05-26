
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
from abc import abstractmethod


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
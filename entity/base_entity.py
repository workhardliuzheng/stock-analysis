from abc import abstractmethod


class BaseEntity:

    def to_dict(self):
        return {key: value for key, value in self.__dict__.items()}

    def to_dict_with_backticks(self, contains_id=True):
        data_dict = self.to_dict()
        if contains_id is not True:
            del data_dict['id']
        return {f'`{key}`': value for key, value in self.__dict__.items()}

    def columns(self):
        return self.__dict__.values()

    @abstractmethod
    def from_list_to_entity(self, list):
        pass
class BaseEntity:
    def to_dict(self):
        return {key: value for key, value in self.__dict__.items()}
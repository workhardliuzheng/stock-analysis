import json


class JsonUtil:
    @staticmethod
    def to_json(obj):
        """
        Convert an object to a JSON string.

        Args:
            obj: The object to convert to JSON.

        Returns:
            A JSON string representation of the object.
        """
        if hasattr(obj, '__dict__'):
            return json.dumps(obj.__dict__)
        else:
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    @staticmethod
    def from_json(json_str, cls):
        """
        Create an object from a JSON string.

        Args:
            json_str: The JSON string to convert to an object.
            cls: The class of the object to create.

        Returns:
            An instance of the specified class created from the JSON string.
        """
        data = json.loads(json_str)
        obj = cls()
        for key, value in data.items():
            if hasattr(obj, f'set_{key}'):
                getattr(obj, f'set_{key}')(value)
            elif hasattr(obj, key):
                setattr(obj, key, value)
            else:
                raise AttributeError(f"Class {cls.__name__} has no attribute or setter for '{key}'")
        return obj
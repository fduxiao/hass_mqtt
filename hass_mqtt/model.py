"""
The module contains the basic data model class.
A model is just a key-value dict. I provide
the :py:class:`Field` class to access the dict data
easily.
"""
try:
    import ujson as json
except ImportError:
    import json


class DefaultFactory:
    """
    Sometimes, we need to make a new instance of default value, e.g, :py:class:`dict`.
    This class is provided as an indicator for `calling it everytime`.
    """
    def __init__(self, func):
        self.func = func

    def __call__(self):
        return self.func()


class Field:
    """
    Field over load __get__ and __set__ to manipulate the data
    of a :py:class:`Model`
    """

    @staticmethod
    def default_cast(x):
        """default cast is just id"""
        return x

    def __init__(self, name=None, default=None, cast=None):
        self.name = name
        self.default = default
        if cast is None:
            cast = self.default_cast
        self.cast = cast

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        default = self.default
        if isinstance(self.default, DefaultFactory):
            default = default()
        value = instance.data.setdefault(self.name, default)
        return self.cast(value)

    def __set__(self, instance, value):
        instance.data[self.name] = value


class Model:
    """
    A model is just a class with a member of type :py:class:`dict` called data.
    """
    default_field_name = "default_field"

    @classmethod
    def as_field(cls, name=None, default=None):
        """
        A field of a :py:class:`Model` can certainly be
        another model. Thus, a class method is provided
        to make a field easily

        :param name:
        :param default:
        :return:
        """
        if name is None:
            name = cls.default_field_name
        if default is None:
            default = DefaultFactory(dict)
        return Field(name, default, cls)

    def __init__(self, data=None):
        if data is None:
            data = {}
        self.data = data


class Config(Model):
    """
    Naturally, a json file can contain a :py:class:`dict`. This
    class is provided for loading a json into data
    """
    def __init__(self, file_path) -> None:
        super().__init__()
        self.load(file_path)

    def load(self, file_path):
        """Load a json file."""
        with open(file_path, 'r') as file:
            self.data = json.load(file)

    def save(self, file_path):
        """Save to a json file."""
        with open(file_path, 'w') as file:
            json.dump(self.data, file)

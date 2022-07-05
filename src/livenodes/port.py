from typing import NamedTuple


class Port():

    example_values = []

    def __init__(self, label, key=None, optional=False):
        self.label = label
        self.optional = optional

        if key is None or type(key) is not str:
            key = label.lower().replace(' ', '_')
        self.key = key
    
    def __str__(self):
        return f"<{self.__class__.__name__}: {self.key}>"

    def __eq__(self, other):
        return type(self) == type(other) \
            and self.key == other.key 

    def __init_subclass__(self):
        if len(self.example_values) <= 0:
            raise Exception('Need to provide at least one example value.')

        for val in self.example_values:
            valid, msg = self.check_value(val)
            if not valid:
                raise Exception(f'Example value does not pass check. Msg: {msg}. Value: {val}')
        return super().__init_subclass__()


    @staticmethod
    def check_value(value):
        raise NotImplementedError()

    @classmethod
    def can_connect_to(cls, other_port_cls):
        # print(list(map(cls.check_value, other_port_cls.example_values)))
        return cls == other_port_cls \
            or any([compatible for compatible, _ in map(cls.check_value, other_port_cls.example_values)])
            # we use any here in order to allow for dynamic converters, e.g. adding or removing axes from a package
            # we could consider using all() instead of any(), but this would require specfic converter nodes, which i'm not sure i want to go for right now
            # but let's keep an eye on this
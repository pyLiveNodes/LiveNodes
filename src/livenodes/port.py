from dataclasses import dataclass


class Port():

    example_values = []

    def __init__(self, label, optional=False):
        self.label = label
        self.optional = optional
    
    # def __str__(self):
    #     return self.label.replace(' ', '_').lower()

    # def __eq__(self, other):
    #     return type(self) == type(other) \
    #         and self.label == other.label 

    def __init_subclass__(self):
        if len(self.example_values) <= 0:
            raise Exception('Need to provide at least on example value.')

        for val in self.example_values:
            valid, msg = self.check_value(val)
            if not valid:
                raise Exception(f'Example value does not pass check. Msg: {msg}. Value: {val}')
    
    @staticmethod
    def check_value(value):
        raise NotImplementedError()

    @classmethod
    def can_connect_to(cls, other_port_cls):
        return cls == other_port_cls \
            or any(map(cls.check_value, other_port_cls.example_values))
            # we use any here in order to allow for dynamic converters, e.g. adding or removing axes from a package
            # we could consider using all() instead of any(), but this would require specfic converter nodes, which i'm not sure i want to go for right now
            # but let's keep an eye on this

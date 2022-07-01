class Port():

    example_values = []

    def __init__(self, name, optional=False):
        self.name = name
        self.optional = optional
    
    def __str__(self):
        return self.name.replace(' ', '_').lower()

    def __eq__(self, other):
        return type(self) == type(other) \
            and self.name == other.name 

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


# TODO: reconsider just using a list instead, i don't feel there is much benefit to this...
class Port_Collection():
    def __init__(self, *ports):
        for port in ports:
            if hasattr(self, f"_{str(port)}"):
                raise ValueError(f'Duplicate ports: {port.name}')
            setattr(self, f"_{str(port)}", port)
        
        self.names = [str(x) for x in ports]
        self.ports = ports
        self.map = dict(zip(self.names, self.ports))

    def __contains__(self, port: Port) -> bool:
        return port in self.ports

    def __iter__(self):
        return iter(self.ports)

    def __len__(self):
        return len(self.ports)

    def get_by_name(self, name):
        return self.map[name]


# import numpy as np

# class Port_Data(Port):

#     example_values = [np.array([[[1]]])]
#     name = 'Data'

#     @staticmethod
#     def check_value(value):
#         if not isinstance(value, np.array):
#             return False, "Should be numpy array;"
#         elif len(value.shape) != 3:
#             return False, "Shape should be of length three (Batch, Time, Channel)"
#         return True, None

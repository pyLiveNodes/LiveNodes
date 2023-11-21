import numpy as np

ALL_VALUES = [
    np.array([[[1]]]),
    ["EMG1", "EMG2"],
    [["EMG1", "EMG2"]],
    [[["EMG1", "EMG2"]]],
    [0, 1],
    [20, .1],
    [[20, .1]],
    [[[20, .1]]],
    20,
    "Foo",
]

class Port():
    example_values = []
    compound_type = None

    def __init__(self, label, optional=False):
        self.label = label
        self.optional = optional

        # Just as a fallback, the key should still be set by the connectionist / node_connector
        self.key = None #label.lower().replace(' ', '_')

    def set_key(self, key):
        if key == None:
            raise ValueError('Key may not be none')
        self.key = key

    def __str__(self):
        return f"<{self.__class__.__name__}: {self.key}>"

    # TODO: figure out if we really need to check the key as well...
    def __eq__(self, other):
        return type(self) == type(other) \
            and self.key == other.key

    def __init_subclass__(cls):
        if cls.compound_type is not None:
            compounded_examples = list(filter(lambda x: cls.check_value(x)[0], map(cls.example_compound_construction, cls.compound_type.example_values)))
            cls.example_values.extend(compounded_examples)

        if len(cls.example_values) <= 0:
            raise Exception('Need to provide at least one example value.')

        for val in cls.example_values:
            valid, msg = cls.check_value(val)
            if not valid:
                raise Exception(f'Example value does not pass check ({str(cls)}). Msg: {msg}. Value: {val}')
            if id(val) not in list(map(id, ALL_VALUES)):
                ALL_VALUES.append(val)
        return super().__init_subclass__()

    @classmethod
    def example_compound_construction(cls, compounding_value):
        raise NotImplementedError()

    @classmethod
    def add_examples(cls, *args):
        cls.example_values.extend(args)

    @classmethod
    def check_value(cls, value):
        raise NotImplementedError()

    @classmethod
    def accepts_inputs(cls, example_values):
        return list(map(cls.check_value, example_values))

    @classmethod
    def can_input_to(emit_port_cls, recv_port_cls):
        # print(list(map(cls.check_value, recv_port_cls.example_values)))
        return emit_port_cls == recv_port_cls \
            or any([compatible for compatible, _ in recv_port_cls.accepts_inputs(emit_port_cls.example_values)])
            # we use any here in order to allow for dynamic converters, e.g. adding or removing axes from a package
            # we could consider using all() instead of any(), but this would require specfic converter nodes, which i'm not sure i want to go for right now
            # but let's keep an eye on this


# unfortunately a stable named tuple implementation with subclassing is not possible with python 3.6
# this is precisely the scenario we would have liked to use: https://github.com/python/typing/issues/526

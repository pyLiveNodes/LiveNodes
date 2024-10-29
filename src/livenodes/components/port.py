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
    {},
]

class Ports_collection():
    # this is the problem we had with NamedTuple summed up: https://peps.python.org/pep-0557/#mutable-default-values
    def __init__(self):
        for key in self._itr_helper():
            # set the key of the port to the key its located under in the port collection 
            setattr(self, key, getattr(self, key).contextualize(key))
    
    def __iter__(self):
        for key in self._itr_helper():
            yield getattr(self, key)
    
    def _itr_helper(self):
        for key in dir(self):
            if not key.startswith('_') and isinstance(getattr(self, key), Port):
                yield key

    def __len__(self):
        return len(list(self._itr_helper()))

    def _asdict(self):
        return {key: getattr(self, key) for key in self._itr_helper()}
    
    @property
    def _fields(self):
        return list(self._itr_helper())


class Port():
    example_values = []
    compound_type = None
    label = 'No Label Set'

    def __init__(self, label=None, optional=False, key=None):
        if label is not None:
            self.label = label
        self.optional = optional
        self.key = key

    def contextualize(self, key):
        if key == None:
            raise ValueError('Key may not be none')
        try:
            return self.__class__(self.label, self.optional, key)
        except:
            raise NotImplementedError(f'Double check if the class {self.__class__} implemenrts the new port interface correctly. I.e. accepts the optional and key arguments.')

    def __str__(self):
        return f"<{self.__class__.__name__}: {self.key}>"

    # TODO: figure out if we really need to check the key as well...
    def __eq__(self, other):
        return type(self) == type(other) \
            and self.key == other.key

    def __init_subclass__(cls):
        if id(cls.example_values) == id(super(cls, cls).example_values):
            raise Exception('Child should not have the same example values as parent. Why is this another port if they share the same values? If you did not want to set values, please set example_values=[]')
        
        if cls.compound_type is not None:
            # We need to do this at runtime, because classes like Any will have changing example values and thus compound values as well
            cls.example_values.extend(cls.all_examples_compound_construction())

        if len(cls.example_values) <= 0:
            raise Exception('Need to provide at least one example value.')

        ids = list(map(id, ALL_VALUES))
        for val in cls.example_values:
            valid, msg = cls.check_value(val)
            if not valid:
                raise Exception(f'Example value does not pass check ({str(cls)}). Msg: {msg}. Value: {val}')
            if id(val) not in ids:
                ALL_VALUES.append(val)
        return super().__init_subclass__()

    @classmethod
    def example_compound_construction(cls, compounding_value):
        raise NotImplementedError()
    
    @classmethod
    def all_examples_compound_construction(cls):
        return list(filter(lambda x: cls.check_value(x)[0], map(cls.example_compound_construction, cls.compound_type.example_values)))

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
        # # print(list(map(cls.check_value, recv_port_cls.example_values)))
        return emit_port_cls == recv_port_cls \
            or any([compatible for compatible, _ in recv_port_cls.accepts_inputs(emit_port_cls.example_values)])
            # we use any here in order to allow for dynamic converters, e.g. adding or removing axes from a package
            # we could consider using all() instead of any(), but this would require specfic converter nodes, which i'm not sure i want to go for right now
            # but let's keep an eye on this


# unfortunately a stable named tuple implementation with subclassing is not possible with python 3.6
# this is precisely the scenario we would have liked to use: https://github.com/python/typing/issues/526
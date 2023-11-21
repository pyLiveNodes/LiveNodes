import pytest

from livenodes.components.port import Port, ALL_VALUES
import numpy as np

# === Special Case Any ========================================================
class Port_Any(Port):
    # TODO: figure out how to automatically extend this with each new primitive (?) port class added...
    example_values = ALL_VALUES

    @classmethod
    def check_value(cls, value):
        return True, None
    

class Port_Int(Port):
    example_values = [
        0,
        1,
        np.array([1])[0]
    ]

    @classmethod
    def check_value(cls, value):
        if not isinstance(value, int):
            try:
                if np.issubdtype(value, np.integer):
                    return True, None
                else:
                    return False, f"Should be int; got {type(value)}, val: {value}."
            except:
                return False, f"Should be int; got {type(value)}, val: {value}."
        return True, None

# === Compounds ========================================================

# TODO: consider if it really makes sense to mix lists and arrays...
class Port_List(Port):
    example_values = []
    compound_type = Port_Any

    @classmethod
    def example_compound_construction(cls, compounding_value):
        return [compounding_value]

    @classmethod
    def check_value(cls, value):
        if not (type(value) == list or isinstance(value, np.ndarray)):
            return False, f"Should be list; got {type(value)}, val: {value}."
        if len(value) > 0:
            return cls.compound_type.check_value(value[-1])
        return True, None

class Port_List_Int(Port_List):
    example_values = [] # as we would otherwise inherit Port_lists (which compounds any, which in turn is incompatible with Port_Int)
    compound_type = Port_Int
    

class TestPorts():

    def test_any_value(self):
        a = Port_Any("")
        assert a.check_value(1)[0]
        assert a.check_value("None")[0]
        assert a.check_value(None)[0]
        assert a.check_value([])[0]
        assert a.check_value([{'a': [5]}])[0]

    def test_int_value(self):
        a = Port_Int("")
        assert a.check_value(1)[0]
        assert a.check_value(-200)[0]
        assert not a.check_value(None)[0]
        assert not a.check_value([])[0]
        assert not a.check_value([1])[0]
        assert not a.check_value([{'a': [5]}])[0]

    def test_list_value(self):
        a = Port_List("")
        assert a.check_value([])[0]
        assert a.check_value([[1]])[0]
        assert a.check_value([[1, -3]])[0]
        assert a.check_value([['1', -3]])[0]
        assert not a.check_value(None)[0]

    def test_list_int_value(self):
        a = Port_List_Int("")
        assert a.check_value([])[0]
        assert a.check_value([1, -1, 2])[0]
        assert not a.check_value([[1]])[0]
        assert not a.check_value([[1, -3]])[0]
        assert not a.check_value([['1', -3]])[0]
        assert not a.check_value(None)[0]


        

if __name__ == "__main__":
    a = Port_List_Int("")
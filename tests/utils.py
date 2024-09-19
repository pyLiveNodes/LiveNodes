from livenodes.components.port import Port

class Port_Ints(Port):

    example_values = [
        0, 1, 20, -15
    ]

    @classmethod
    def check_value(cls, value):
        if type(value) != int:
            return False, f"Should be int; got: {type(value)}."
        return True, None

class Port_Str(Port):
    example_values = [
        "Some example value",
        "another_one"
    ]

    @classmethod
    def check_value(cls, value):
        if type(value) != str:
            return False, f"Should be string; got {type(value)}."
        return True, None
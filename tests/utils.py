from livenodes.components.port import Port

class Port_Ints(Port):

    example_values = [
        0, 1, 20, -15
    ]

    def __init__(self, name='Int', optional=False):
        super().__init__(name, optional)

    @classmethod
    def check_value(cls, value):
        if type(value) != int:
            return False, "Should be int;"
        return True, None

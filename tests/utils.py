from livenodes.components.port import Port

class Port_List_of_Ints(Port):

    example_values = [
        [0, 1, 20, -15]
    ]

    def __init__(self, name='File', optional=False):
        super().__init__(name, optional)

    @staticmethod
    def check_value(value):
        if not (type(value) == list and type(value[0]) == int):
            return False, "Should be list of ints;"
        return True, None

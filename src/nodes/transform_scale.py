import numpy as np
from .node import Node

class Transform_scale(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Transform"
    description = "" 

    example_init = {'name': 'Name'}

    def __init__(self, in_min, in_max, name = "Scaler", **kwargs):
        super().__init__(name=name, **kwargs)

        self.in_min = in_min
        self.in_max = in_max

        self.divisor = (in_min + in_max) / 2

    def _settings(self):
        return {\
            "in_min": self.in_min,
            "in_max": self.in_max,
            "name": self.name,
           }

    def process(self, data):
        res = (np.array(data) - self.in_min) / self.divisor - 1
        self._emit_data(res)

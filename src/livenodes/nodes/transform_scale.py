import numpy as np

from livenodes.core.node import Node

from . import local_registry

@local_registry.register
class Transform_scale(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Transform"
    description = ""

    example_init = {'name': 'Name'}

    def __init__(self, in_min, in_max, name="Scaler", **kwargs):
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

    def process_time_series(self, ts):
        return (np.array(ts) - self.in_min) / self.divisor - 1

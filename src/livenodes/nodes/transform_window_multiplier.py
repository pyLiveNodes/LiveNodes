import numpy as np

from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Transform_window_multiplier(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Transform"
    description = ""

    example_init = {'name': 'Name'}

    def __init__(self, function, name="Window", **kwargs):
        super().__init__(name=name, **kwargs)

        self.function = function

    def _settings(self):
        return {\
            "name": self.name,
            "function": self.function
           }

    def process_time_series(self, ts):
        d = np.array(ts)
        multiplier = getattr(np, function)(d.shape[0])
        return d * multiplier

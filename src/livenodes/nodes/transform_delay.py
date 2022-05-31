import numpy as np
from functools import reduce

from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Transform_delay(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Transform"
    description = ""

    example_init = {'name': 'Delay', 'n_calls': 0}

    def __init__(self, n_calls=0, name="Delay", **kwargs):
        super().__init__(name=name, **kwargs)

        self.n_calls = n_calls
        self.ctr = 0
        self.last_values = {}

    def _settings(self):
        return {"n_calls": self.n_calls}

    def process(self, data, **kwargs):
        if self.ctr in self.last_values:
            self._emit_data(self.last_values[self.ctr])

        self.last_values[self.ctr] = data
        self.ctr = (self.ctr + 1) % self.n_calls

import numpy as np
from functools import reduce

from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Mimic_variable(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Mimic"
    description = ""

    example_init = {'name': 'Variable Mimic', 'value': -1}

    # TODO: technically this is a special case of the mimic last input, consider merging. (it's a purely esthetical / testing difference)

    def __init__(self, value=0, name="Variable Mimic", **kwargs):
        super().__init__(name=name, **kwargs)

        self.value = value

    def _settings(self):
        return {"value": self.value}

    def process(self, data, **kwargs):
        d = np.array(data, dtype=object)
        r = d.size
        if len(d.shape) > 0:
            r = d.shape[0]

        self._emit_data(np.repeat(self.value, r))

import numpy as np
from functools import reduce

from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Transform_add_dims(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Transform"
    description = ""

    example_init = {'name': 'To Data', 'add_n_dims': 0}

    def __init__(self, add_n_dims=0, name="To Data", **kwargs):
        super().__init__(name=name, **kwargs)

        self.add_n_dims = add_n_dims

    def _settings(self):
        return {"add_n_dims": self.add_n_dims}

    def process(self, data, **kwargs):
        self._emit_data(np.expand_dims(data, tuple(range(self.add_n_dims))))

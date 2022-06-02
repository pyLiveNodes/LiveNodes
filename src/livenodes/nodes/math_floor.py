import numpy as np
from functools import reduce

from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Math_floor(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Transform"
    description = ""

    example_init = {'name': 'Floor'}

    def process(self, data, **kwargs):
        self._emit_data(np.floor(data).astype(np.int))

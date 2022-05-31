import numpy as np
from functools import reduce

from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Math_subtract(Node):
    channels_in = ['Data 1', 'Data 2']
    channels_out = ['Data']

    category = "Transform"
    description = ""

    example_init = {'name': 'Subtract'}

    def _should_process(self, data_1=None, data_2=None):
        return data_1 is not None \
            and data_2 is not None

    def process(self, data_1, data_2, **kwargs):
        # for now let's just assume they have equal sizes or are broadcastable
        self._emit_data(np.subtract(data_1, data_2))

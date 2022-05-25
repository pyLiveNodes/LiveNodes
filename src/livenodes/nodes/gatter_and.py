import numpy as np
from functools import reduce

from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Gatter_and(Node):
    channels_in = ['Trigger 1', "Trigger 2"]
    channels_out = ['Trigger']

    category = "Transform"
    description = ""

    example_init = {'name': 'Logical and'}

    def _should_process(self, trigger_1=None, trigger_2=None):
        return trigger_1 is not None and \
            trigger_2 is not None

    def process(self, trigger_1, trigger_2, **kwargs):
        self._emit_data(np.logical_and(trigger_1, trigger_2), channel='Trigger')

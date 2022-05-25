import numpy as np
from functools import reduce

from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Gatter_not(Node):
    channels_in = ['Trigger']
    channels_out = ['Trigger']

    category = "Transform"
    description = ""

    example_init = {'name': 'Logical not'}

    def _should_process(self, trigger=None):
        return trigger is not None

    def process(self, trigger, **kwargs):
        self._emit_data(np.logical_not(trigger), channel='Trigger')

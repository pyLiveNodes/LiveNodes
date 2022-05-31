import numpy as np
from functools import reduce

from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Variable_mimic(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Transform"
    description = ""

    example_init = {'name': 'To Data', 'value': -1}

    def __init__(self, value=0, name="To Data", **kwargs):
        super().__init__(name=name, **kwargs)

        self.value = value

    def _settings(self):
        return {"value": self.value}

    def process(self, data, **kwargs):
        self._emit_data([self.value] * len(data))

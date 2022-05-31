import numpy as np
from functools import reduce

from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Mimic_last_input(Node):
    channels_in = ['Input', 'Data']
    channels_out = ['Data']

    category = "Mimic"
    description = ""

    example_init = {'name': 'Variable Mimic', 'fallback_value': -1}

    def __init__(self, fallback_value=-1, name="Variable Mimic", **kwargs):
        super().__init__(name=name, **kwargs)

        self.fallback_value = fallback_value
        self.last_value = fallback_value

    def _settings(self):
        return {"fallback_value": self.fallback_value}

    def _should_process(self, data=None, input=None):
        # always process if one of the two is available
        return data is not None \
            or input is not None
        
    def process(self, data=None, input=None, **kwargs):
        if input is not None:
            # TODO: this is a multiprocessing hazard, as the input and data calls may come from different processes
            self.last_value = input
        if data is not None:
            self._emit_data(self.last_value)

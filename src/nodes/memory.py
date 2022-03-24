import numpy as np
from .node import Node

class Memory(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Basic"
    description = "" 

    example_init = {'name': 'Name'}

    def __init__(self, length=None, name = "Memory", **kwargs):
        super().__init__(name=name, **kwargs)
        self.length = length
        self.buffer = []


    def _settings(self):
        return {\
            "length": self.length
           }

    def process(self, data, **kwargs):
        self.buffer.extend(data_frame)
        if self.length != None:
            self.buffer = self.buffer[-self.length:]
        self._emit_data(self.buffer)

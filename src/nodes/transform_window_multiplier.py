import numpy as np
from .node import Node

class Transform_window_multiplier(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Transform"
    description = "" 

    example_init = {'name': 'Name'}

    def __init__(self, function, name = "Window", **kwargs):
        super().__init__(name=name, **kwargs)

        self.function = function
    
        
    def _settings(self):
        return {\
            "name": self.name,
            "function": self.function
           }

    def process(self, data):
        multiplier = getattr(np, function)(len(data))
        self._emit_data(np.multiply(np.array(self.buffer[:self.length]), multiplier))

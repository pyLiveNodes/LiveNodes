import numpy as np
from .node import Node

class Transform_window_multiplier(Node):
    def __init__(self, function, name = "Window", dont_time = False):
        super().__init__(name=name, dont_time=dont_time)
        self.function = function
    
    @staticmethod
    def info():
        return {
            "class": "Transform_window_multiplier",
            "file": "Transform_window_multiplier.py",
            "in": ["Data"],
            "out": ["Data"],
            "init": {}, #TODO!
            "category": "Transform"
        }
        
    def _get_setup(self):
        return {\
            "name": self.name,
            "function": self.function
           }

    def receive_data(self, data_frame, **kwargs):
        multiplier = getattr(np, function)(len(data_frame))
        self.send_data(np.multiply(np.array(self.buffer[:self.length]), multiplier))

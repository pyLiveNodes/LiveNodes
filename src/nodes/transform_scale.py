import numpy as np
from .node import Node

class Transform_scale(Node):
    def __init__(self, in_min, in_max, name = "Scaler", dont_time = False):
        super().__init__(name=name, dont_time=dont_time)
        self.in_min = in_min
        self.in_max = in_max

        self.divisor = (in_min + in_max) / 2

        self.buffer = []
    
    @staticmethod
    def info():
        return {
            "class": "Transform_scale",
            "file": "Transform_scale.py",
            "in": ["Data"],
            "out": ["Data"],
            "init": {}, #TODO!
            "category": "Transform"
        }

    def _get_setup(self):
        return {\
            "in_min": self.in_min,
            "in_max": self.in_max,
            "name": self.name,
           }

    def receive_data(self, data_frame, **kwargs):
        res = (np.array(data_frame) - self.in_min) / self.divisor - 1
        self.send_data(res)

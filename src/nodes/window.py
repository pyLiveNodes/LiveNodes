import numpy as np
from .node import Node

class Window(Node):
    def __init__(self, length, overlap, function="rectangular", name = "Window", dont_time = False):
        super().__init__(name=name, dont_time=dont_time)
        self.length = length
        self.overlap = overlap
        self.function = function

        if hasattr(np, function):
            self.multiplier = getattr(np, function)(length)
        elif function != 'rectangular':
            raise Exception(f'Window type "{function}" does not exist in the numpy module and is not rectangular')
        else:
            # self.multiplier = np.ones(length)
            self.multiplier = 1

        self.buffer = []
    
    def _get_setup(self):
        return {\
            "length": self.length,
            "overlap": self.overlap,
            "function": self.function
           }

    def receive_data(self, data_frame, **kwargs):
        self.buffer.extend(data_frame)
        while len(self.buffer) >= self.length:
            # print(np.array(self.buffer[:self.length]).shape, self.multiplier.shape)
            self.send_data(np.multiply(np.array(self.buffer[:self.length]), self.multiplier))
            self.buffer = self.buffer[(self.length - self.overlap):]

import numpy as np
from .node import Node

class Transform_window(Node):
    def __init__(self, length, overlap, name = "Window", dont_time = False):
        super().__init__(name=name, dont_time=dont_time)
        self.length = length
        self.overlap = overlap

        self.buffer = []
    
    def _get_setup(self):
        return {\
            "length": self.length,
            "overlap": self.overlap,
           }

    def receive_data(self, data_frame, **kwargs):
        self.buffer.extend(data_frame)
        # TODO: consider if we could send mulitple frames in one send_data call or if that breaks an assumption later on
        # benefits would be more performant feature calculation (for example), but prob. the whole pipline might see minor benefits
        while len(self.buffer) >= self.length:
            # print(np.array(self.buffer[:self.length]).shape, self.multiplier.shape)
            self.send_data(self.buffer[:self.length])
            self.buffer = self.buffer[(self.length - self.overlap):]

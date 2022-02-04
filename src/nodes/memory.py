import numpy as np
from .node import Node

class Memory(Node):
    def __init__(self, length=None, name = "Memory", dont_time = False):
        super().__init__(name=name, dont_time=dont_time)
        self.length = length
        self.buffer = []
    
    def _get_setup(self):
        return {\
            "length": self.length
           }

    def receive_data(self, data_frame, **kwargs):
        self.buffer.extend(data_frame)
        if self.length != None:
            self.buffer = self.buffer[-self.length:]
        self.send_data(self.buffer)

import numpy as np
from .node import Node
import time

class Debug_frame_counter(Node):

    def __init__(self, name="Frame Counter", **kwargs):
        super().__init__(name, **kwargs)
        self.counter = 0
        self.time = None

    @staticmethod
    def info():
        return {
            "class": "Debug_frame_counter",
            "file": "Debug_frame_counter.py",
            "in": ["Data"],
            "out": ["Data"],
            "init": {
                "name": "Frame Counter"
            },
            "category": "Debug"
        }
        
    def process(self, data, **kwargs):
        if self.time is None:
            self.time = time.time()
            
        self.counter += len(data_frame)
        if self.counter % 100 == 0:
            t2 = time.time() - self.time
            fps = self.counter / t2
            print(f"{self.name}; received {self.counter} frames in {t2:.2f} seconds. This equals {fps:.2f}Hz.")

        self._emit_data(data_frame)
        
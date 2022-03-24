# import numpy as np
# from .node import Node
# import time

# class Debug_frame_counter(Node):
#     channels_in = ['Data']
#     channels_out = ['Data']

#     category = "Debug"
#     description = "" 

#     example_init = {'name': 'Frame Counter'}

#     def __init__(self, name="Frame Counter", **kwargs):
#         super().__init__(name, **kwargs)

#         self.counter = 0
#         self.time = None
        
#     def process(self, data):
#         if self.time is None:
#             self.time = time.time()
            
#         self.counter += len(data)
#         if self.counter % 100 == 0:
#             t2 = time.time() - self.time
#             fps = self.counter / t2
#             print(f"{self.name}; received {self.counter} frames in {t2:.2f} seconds. This equals {fps:.2f}Hz.")

#         self._emit_data(data)
        
This should be replaced by the internal clock being initialized with time, ie -> the main node should provide profiling information
import numpy as np
from .node import Node

class Transform_window(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Transform"
    description = "" 

    example_init = {'name': 'Name'}
    
    def __init__(self, length, overlap, name = "Window", **kwargs):
        super().__init__(name=name, **kwargs)

        self.length = length
        self.overlap = overlap

        self.buffer = []

    def _settings(self):
        return {\
            "length": self.length,
            "overlap": self.overlap,
            "name": self.name,
           }

    def _retrieve_current_data(self):
        return { 
            # as we have only one input that may be connected and this function is only ever called if _process is called, we can this this way
            # TODO: test the heck out of this and the clock system! This still feels hacky
            # TODO: we currently are assuming, that the item we are getting here is also the last one put into the queue....
            'data': self._received_data['Data'].queue.get()[1]
        }

    def process(self, data):
        self.buffer.extend(data)
        # self._log(data.shape, np.array(self.buffer).shape)
        # TODO: consider if we could send mulitple frames in one send_data call or if that breaks an assumption later on
        # benefits would be more performant feature calculation (for example), but prob. the whole pipline might see minor benefits
        # -> tried, doesn't seem worth the trouble
            # -> only really applies to offline processing, and makes all pipeline steps a lot more complex, because suddendly they need to consider more dimensions
            # -> res: only do if really bored/or working a lot more on offline data
        # send = []
        ctr = 0
        while len(self.buffer) >= self.length:
            # print(np.array(self.buffer[:self.length]).shape, self.multiplier.shape)
            # self.buffer should be (time, channels) and now becomes (1, channels, time)
            # self._log('Emitting', self.buffer[:self.length])
            self._emit_data(self.buffer[:self.length])
            # self._emit_data([np.array(self.buffer[:self.length]).T])
            # send.append(np.array(self.buffer[:self.length]).T)
            # send.append(self.buffer[:self.length])
            self.buffer = self.buffer[(self.length - self.overlap):]

            ctr += 1
        # self._emit_data(send)
        return ctr > 0

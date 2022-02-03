import numpy as np
import multiprocessing as mp

from .node import Node

class Filter(Node):
    def __init__(self, names, name = "Channel Filter", dont_time = False):
        super().__init__(name=name, dont_time=dont_time)
        self.names = names

        self.received_channel_names = False
        self._wait_queue = mp.Queue()

    def _get_setup(self):
        return {\
            "name": self.name,
            "names": self.names
           }

    def receive_channels(self, channel_names, **kwargs):
        self.idx = np.isin(channel_names, self.names)
        self.received_channel_names = True

        self.send_data(self.names, data_stream="Channel Names")

        # forward all temporary stored data
        while not self._wait_queue.empty():
            self.receive_data(self._wait_queue.get())
        
    def receive_data(self, data_frame, **kwargs):
        if self.received_channel_names:
            self.send_data(np.array(data_frame)[:,self.idx])
        else:
            self._wait_queue.put(data_frame)
            if self._wait_queue.qsize() > 50:
                raise Exception('It seems you forgot to hook up the channel names input? The tmp queue is overflowing')

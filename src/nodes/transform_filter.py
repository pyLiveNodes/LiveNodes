import numpy as np
import multiprocessing as mp

from .node import Node

class Transform_filter(Node):
    channels_in = ['Data', 'Channel Names']
    channels_out = ['Data', 'Channel Names']

    category = "Transform"
    description = "" 

    example_init = {'name': 'Channel Filter'}

    def __init__(self, names, name = "Channel Filter", **kwargs):
        super().__init__(name=name, **kwargs)
        
        self.names = names
        self.received_channel_names = False

        self.idx = None
        
    def _settings(self):
        return {\
            "name": self.name,
            "names": self.names
           }

    def _should_process(self, data, channel_names):
        # any data received before the clock in which we receive the channel names will be discarded
        # we could consider a wait_queue as before, but not sure if needed -> TODO write tests!
        #   -> pro: would allow to 100% not loose data
        #   -> con: if channels change (possible with user input in parent nodes) ...? think this through! 
        return (data is not None) and (self.received_channel_names or channel_names is not None)

    def process(self, data, channel_names):
        if channel_names is not None:
            # yes, seems less efficient than np.isin, but implicitly re-orders the channels of the output to match the provided names
            self.idx = [channel_names.index(x) for x in self.names]
            self.received_channel_names = True

            self._emit_data(self.names, channel="Channel Names")
        
        self._emit_data(np.array(data)[:,self.idx])

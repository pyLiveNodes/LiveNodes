import numpy as np

from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Buffer_stream_switch(Node):
    # Toggle must be a single integer, not a list
    channels_in = ['Data 1', 'Data 2', 'Toggle']
    channels_out = ['Data']

    category = "Transform"
    description = ""

    example_init = {'name': 'Stream Switch'}

    def __init__(self, name="Name", **kwargs):
        super().__init__(name, **kwargs)

        self.last_sent_clock = -1
        self.buffer_1 = []
        self.buffer_2 = []
        
        self.index_helper = np.array(['buffer_1', 'buffer_2'])

    # Alg: 
    # a) The stream that we are toggled to has data -> process by sending the data and remembering, that we did so
    # b) The stream that we are not toggled to also sends us data -> buffer that, ie process again, but do not re-send a)
    def _should_process(self, toggle=None, data_1=None, data_2=None):
        # this expression will trigger once or twice if both data_1 and data_2 provide data
        # case with one trigger:
        # on clock 1 (toggle = 0) -> do not process
        # on clock 1 (toggle = 0, data_2) -> do not process
        # on clock 1 (toggle = 0, data_2, data_1) -> process!
        # case with two triggers:
        # on clock 1 (toggle = 0) -> do not process
        # on clock 1 (toggle = 0, data_1) -> process!
        # on clock 1 (toggle = 0, data_1, data_2) -> process!
        return (toggle == 0 and data_1 is not None) \
            or (toggle == 1 and data_2 is not None)

    def process(self, toggle, _ctr, data_1=None, data_2=None, **kwargs):
        data_to_send, data_to_buffer = [data_1, data_2][toggle]
        buffer_to_empty, buffer_to_fill = self.index_helper[toggle, int(not toggle)]
        
        # TODO: i'm not sure if we can should actually send multiple emits in one call!
        # IMPORTANT: do check that! it's very likely, that this results in lost data!
        # TODO: -> this is solved now by uncommenting the code below, however, do check if the node code would detect something like this and issue a warning or error

        # # first send all data in our buffer for this toggle
        # for item in getattr(self, buffer_to_empty):
        #     self._emit_data(item)
        # setattr(self, buffer_to_empty, [])

        # send data
        # the _ctr is important, as `process` might (and should) be called twice once for stream 1 and once for stream 1 and 2
        # where the data for stream 1 is the same in both calls as it's on the same clock, see self._should_process
        if _ctr > self.last_sent_clock:
            to_send = []
            # TODO: check if this extension has any implications on nodes behind, as the batch size differs from values from before
            
            # add data from buffer
            for item in getattr(self, buffer_to_empty):
                to_send.extend(item)
            setattr(self, buffer_to_empty, [])

            # add data from this call
            to_send.extend(data_to_send)

            # Note: since we only send once within our clock, the clock actually is the same as from our parents
            self._emit_data(to_send)
            self.last_sent_clock = _ctr
        
        # store potential data from the other stream to be sent later
        if data_to_buffer is not None:
            getattr(self, buffer_to_fill).append(data_to_buffer)

import numpy as np

from livenodes.core.sender_blocking import BlockingSender

import plux

from . import local_registry

@local_registry.register
class NewDevice(plux.SignalsDev):
    """
    Stub for a Plux based device.
    The onRawFrame should be overwritten
    """

    def __init__(self, address):
        plux.MemoryDev.__init__(address)
        self.onRawFrame = lambda _: None

    # From the doc/examples:
    #
    # https://github.com/biosignalsplux/python-samples/blob/master/MultipleDeviceThreadingExample.py
    # Supported channel number codes:
    # {1 channel - 0x01, 2 channels - 0x03, 3 channels - 0x07
    # 4 channels - 0x0F, 5 channels - 0x1F, 6 channels - 0x3F
    # 7 channels - 0x7F, 8 channels - 0xFF}
    # Maximum acquisition frequencies for number of channels:
    # 1 channel - 8000, 2 channels - 5000, 3 channels - 4000
    # 4 channels - 3000, 5 channels - 3000, 6 channels - 2000
    # 7 channels - 2000, 8 channels - 2000

    # DEBUG NOTE:
    # It seems to work best when activating the plux hub and shortly after starting the pipline in qt interface
    # (which is weird) as on command line the timing is not important at all...


class In_biosignalsplux(BlockingSender):
    """
    Feeds data frames from a biosiagnal plux based device into the pipeline.

    Examples for biosignal plux devices are: biosignalplux hup and muscleban (for RIoT and Bitalino please have a look at in_riot.py)

    Requires the plux libaray.
    """

    channels_in = []
    channels_out = ['Data', 'Channel Names']

    category = "Data Source"
    description = ""

    example_init = {
        "adr": "mac address",
        "freq": 100,
        "channel_names": ["Channel 1"],
        "n_bits": 16,
        "name": "Biosignalsplux",
    }

    def __init__(self,
                 adr,
                 freq,
                 channel_names=[],
                 n_bits=16,
                 name="Biosignalsplux",
                 **kwargs):
        super().__init__(name, **kwargs)

        self.adr = adr
        self.freq = freq
        self.n_bits = n_bits
        self.channel_names = channel_names

        self.device = None

    def _settings(self):
        return {\
            "adr": self.adr,
            "freq": self.freq,
            "n_bits": self.n_bits,
            "channel_names": self.channel_names
        }

    def _onstop(self):
        self.device.stop()
        self.device.close()

    def _onstart(self):
        """
        Streams the data and calls frame callbacks for each frame.
        """

        def onRawFrame(nSeq, data):
            d = np.array(data)
            # if nSeq % 1000 == 0:
            #     print(nSeq, d, d.shape)
            self._emit_data([[data]])

        self._emit_data(self.channel_names, channel="Channel Names")

        self.device = NewDevice(self.adr)
        self.device.frequency = self.freq

        # TODO: consider moving the start into the init and assign noop, then here overwrite noop with onRawFrame
        # Idea: connect pretty much as soon as possible, but only pass data once the rest is also ready
        # but: make sure to use the correct threads/processes :D
        self.device.onRawFrame = onRawFrame
        # self.device.start(self.device.frequency, 0x01, 16)
        # convert len of channel_names to bit mask for start (see top, or: https://github.com/biosignalsplux/python-samples/blob/master/MultipleDeviceThreadingExample.py)
        self.device.start(self.device.frequency,
                          2**len(self.channel_names) - 1, self.n_bits)
        self.device.loop(
        )  # calls self.device.onRawFrame until it returns True

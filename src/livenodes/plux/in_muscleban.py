import numpy as np

from livenodes.core.sender_blocking import BlockingSender

import plux

from . import local_registry


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

@local_registry.register
class In_muscleban(BlockingSender):
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
        "n_bits": 16,
        "name": "Biosignalsplux",
    }

    channel_names = [ "EMG1"
            "ACC_X", "ACC_Y", "ACC_Z", 
            "MAG_X", "MAG_Y", "MAG_Z"]

    def __init__(self,
                 adr,
                 freq,
                 n_bits=16,
                 name="Biosignalsplux",
                 **kwargs):
        super().__init__(name, **kwargs)

        self.adr = adr
        self.freq = freq
        self.n_bits = n_bits

        self.device = None

    def _settings(self):
        return {\
            "adr": self.adr,
            "freq": self.freq,
            "n_bits": self.n_bits
        }

    def _onstop(self):
        self.device.stop()
        self.device.close()

    def _onstart(self):
        """
        Streams the data and calls frame callbacks for each frame.
        """

        def onRawFrame(nSeq, data):
            # d = np.array(data)
            # if nSeq % 1000 == 0:
            #     print(nSeq, d, d.shape)
            self._emit_data([[data]])

        self._emit_data(self.channel_names, channel="Channel Names")

        self.device = NewDevice(self.adr)

        # TODO: consider moving the start into the init and assign noop, then here overwrite noop with onRawFrame
        # Idea: connect pretty much as soon as possible, but only pass data once the rest is also ready
        # but: make sure to use the correct threads/processes :D
        self.device.onRawFrame = onRawFrame

        emg_channel_src = plux.Source()
        emg_channel_src.port = 1 # Number of the port used by this channel.
        emg_channel_src.freqDivisor = 1 # Subsampling factor in relation with the freq, i.e., when this value is 
                                        # equal to 1 then the channel collects data at a sampling rate identical to the freq, 
                                        # otherwise, the effective sampling rate for this channel will be freq / freqDivisor
        emg_channel_src.nBits = self.n_bits # Resolution in #bits used by this channel.
        emg_channel_src.chMask = 0x01 # Hexadecimal number defining the number of channels streamed by this port, for example:
                                    # 0x07 ---> 00000111 | Three channels are active.
        # [3xACC + 3xMAG]
        acc_mag_channel_src = plux.Source()
        acc_mag_channel_src.port = 2 # or 11 depending on the muscleBAN hardware version.
        acc_mag_channel_src.freqDivisor = 1
        acc_mag_channel_src.nBits = self.n_bits
        acc_mag_channel_src.chMask = 0x3F # 0x3F to activate the 6 sources (3xACC + 3xMAG) of the Accelerometer and Magnetometer sensors.
        
        self.device.start(self.freq, [emg_channel_src, acc_mag_channel_src])
        
        # calls self.device.onRawFrame until it returns True
        self.device.loop() 

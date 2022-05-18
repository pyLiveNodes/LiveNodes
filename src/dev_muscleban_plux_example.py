from livenodes.plux import plux

class NewDevice(plux.SignalsDev):
    def __init__(self, address):
        self.time = 0 # The acquisition will be stopped after self.time seconds.
        self.frequency = 1 # Hz
        
    def onRawFrame(self, nSeq, data):  # onRawFrame takes three arguments
        # if nSeq % self.frequency == 0:
        #     print(nSeq, data)
        print(data)
        return nSeq > self.frequency * self.time


def exampleAcquisition(address, time, freq):  # time acquisition for each frequency
    """
    Example acquisition.
    Maximum acquisition frequencies for number of channels:
    1 channel - 8000, 2 channels - 5000, 3 channels - 4000
    4 channels - 3000, 5 channels - 3000, 6 channels - 2000
    7 channels - 2000, 8 channels - 2000
    """
    device = NewDevice(address)
    device.time = time  # interval of acquisition
    device.frequency = freq
    
    # Definition of the channel sources.
    # [EMG]
    emg_channel_src = plux.Source()
    emg_channel_src.port = 1 # Number of the port used by this channel.
    emg_channel_src.freqDivisor = 1 # Subsampling factor in relation with the freq, i.e., when this value is 
                                    # equal to 1 then the channel collects data at a sampling rate identical to the freq, 
                                    # otherwise, the effective sampling rate for this channel will be freq / freqDivisor
    emg_channel_src.nBits = 16 # Resolution in #bits used by this channel.
    emg_channel_src.chMask = 0x01 # Hexadecimal number defining the number of channels streamed by this port, for example:
                                  # 0x07 ---> 00000111 | Three channels are active.
    # [3xACC + 3xMAG]
    acc_mag_channel_src = plux.Source()
    acc_mag_channel_src.port = 2 # or 11 depending on the muscleBAN hardware version.
    acc_mag_channel_src.freqDivisor = 1
    acc_mag_channel_src.nBits = 16
    acc_mag_channel_src.chMask = 0x3F # 0x3F to activate the 6 sources (3xACC + 3xMAG) of the Accelerometer and Magnetometer sensors.
    
    device.start(device.frequency, [emg_channel_src, acc_mag_channel_src])
    device.loop()  # calls device.onRawFrame until it returns True
    device.stop()
    device.close()


"""
Example acquisition with muscleBAN.
"""

adr = "BTH58:8E:81:A2:49:FC"
freq = 50
exampleAcquisition(adr, 10, freq)

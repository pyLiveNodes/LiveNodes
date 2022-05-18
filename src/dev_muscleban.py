from livenodes.plux import plux

def onRawFrame(nSeq, data):  # onRawFrame takes three arguments
    if nSeq % 1000 == 0:
        print(nSeq, data)
    return nSeq > 1000 * 30


class NewDevice(plux.SignalsDev):

    def __init__(self, address):
        plux.MemoryDev.__init__(address)
        self.onRawFrame = lambda _: None


def exampleAcquisition(address, time, freq,
                       code):  # time acquisition for each frequency
    """
    Example acquisition.
    Supported channel number codes:
    {1 channel - 0x01, 2 channels - 0x03, 3 channels - 0x07
    4 channels - 0x0F, 5 channels - 0x1F, 6 channels - 0x3F
    7 channels - 0x7F, 8 channels - 0xFF}
    Maximum acquisition frequencies for number of channels:
    1 channel - 8000, 2 channels - 5000, 3 channels - 4000
    4 channels - 3000, 5 channels - 3000, 6 channels - 2000
    7 channels - 2000, 8 channels - 2000
    """
    device = NewDevice(address)
    device.time = time  # interval of acquisition
    device.onRawFrame = onRawFrame
    device.frequency = freq
    device.start(device.frequency, code, 8)
    device.loop()  # calls device.onRawFrame until it returns True
    device.stop()
    device.close()


"""
Example acquisition.
Supported channel number codes:
{1 channel - 0x01, 2 channels - 0x03, 3 channels - 0x07
4 channels - 0x0F, 5 channels - 0x1F, 6 channels - 0x3F
7 channels - 0x7F, 8 channels - 0xFF}
Maximum acquisition frequencies for number of channels:
1 channel - 8000, 2 channels - 5000, 3 channels - 4000
4 channels - 3000, 5 channels - 3000, 6 channels - 2000
7 channels - 2000, 8 channels - 2000
"""

adr_mb = "58:8E:81:A2:49:FC"
adr_mb2 = "84:FD:27:E5:04:C4"
adr_bplx = "00:07:80:B3:83:ED"

adr = adr_mb
freq = 100

# exampleAcquisition(f"BTH{adr}", 20, freq, 0x01)
exampleAcquisition(f"{adr}", 20, freq, 0x05)
# exampleAcquisition(f"BLE{adr}", 20, freq, 0x01)

# from src.nodes.in_biosignalsplux import In_biosignalsplux
# from src.nodes.log_data import Log_data

# pl = In_biosignalsplux(adr, freq, channel_names=["Test"], compute_on=Location.PROCESS)
# log = Log_data(compute_on=Location.PROCESS)
# log.connect_inputs_to(pl)
# pl.start()
# time.sleep(5)
# pl.stop()

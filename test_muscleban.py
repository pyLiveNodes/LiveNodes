import platform
import sys

# osDic = {"Darwin": "MacOS",
#          "Linux": "Linux64",
#          "Windows":("Win32_37","Win64_37")}
# if platform.system() != "Windows":
#     sys.path.append("PLUX-API-Python3/{}/plux.so".format(osDic[platform.system()]))
# else:
#     if platform.architecture()[0] == '64bit':
#         sys.path.append("PLUX-API-Python3/Win64_37")
#     else:
#         sys.path.append("PLUX-API-Python3/Win32_37")
import plux


def onRawFrame(nSeq, data):  # onRawFrame takes three arguments
    if nSeq % 1000 == 0:
        print(nSeq, data)
    return nSeq > 1000 * 30

class NewDevice(plux.SignalsDev):
    def __init__(self, address):
        plux.MemoryDev.__init__(address)
        self.onRawFrame = lambda _: None


# example routines


def exampleAcquisition(address, time, freq, code):  # time acquisition for each frequency
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
    device.start(device.frequency, code, 16)
    device.loop()  # calls device.onRawFrame until it returns True
    device.stop()
    device.close()


adr_mb = "88:6B:0F:94:47:C2"
adr_mb2 = "B0:B4:48:B4:94:2C"
adr_bplx = "00:07:80:B3:83:ED"

adr = adr_bplx
freq = 1000

# exampleAcquisition(f"BTH{adr}", 20, freq, 0x01)
# exampleAcquisition(f"{adr}", 20, freq, 0x01)
# exampleAcquisition(f"BLE{adr}", 20, freq, 0x01)


from src.nodes.in_biosignalsplux import In_biosignalsplux

pl = In_biosignalsplux(adr, freq, channel_names=["Pushbutton"])
pl.add_output(lambda data, **kwargs: print(data))

pl.start_processing()
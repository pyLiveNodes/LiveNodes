
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

adr_mb = "88:6B:0F:94:47:C2"
adr_mb2 = "B0:B4:48:B4:94:2C"
adr_bplx = "00:07:80:B3:83:ED"

adr = adr_bplx
freq = 1000

# exampleAcquisition(f"BTH{adr}", 20, freq, 0x01)
# exampleAcquisition(f"{adr}", 20, freq, 0x01)
# exampleAcquisition(f"BLE{adr}", 20, freq, 0x01)


from src.nodes.in_biosignalsplux import In_biosignalsplux
from src.nodes.log_data import Log_data

pl = In_biosignalsplux(adr, freq, channel_names=["Pushbutton"])
pl.add_output(Log_data())
pl.start_processing()
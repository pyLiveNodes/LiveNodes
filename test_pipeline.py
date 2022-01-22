from src.nodes.playback import Playback
from src.nodes.draw_lines import Draw_lines

import numpy as np
import matplotlib.pyplot as plt

pl = Playback(files="./data/KneeBandageCSL2018/**/*.h5", sample_rate=1000)

pl.add_output(lambda data: print(data))

channel_names = ['Gonio2', 'GyroLow1', 'GyroLow2', 'GyroLow3']
recorded_channels = [
    'EMG1', 'EMG2', 'EMG3', 'EMG4',
    'Airborne',
    'AccUp1', 'AccUp2', 'AccUp3',
    'Gonio1',
    'AccLow1', 'AccLow2', 'AccLow3',
    'Gonio2',
    'GyroUp1', 'GyroUp2', 'GyroUp3',
    'GyroLow1', 'GyroLow2', 'GyroLow3']
idx = np.isin(recorded_channels, channel_names).nonzero()[0]

fig, ax = plt.subplots()
draw = Draw_lines(name='Raw Data', subfig=fig, idx=idx, names=channel_names)

pl.add_output(draw)

pl.start_processing()
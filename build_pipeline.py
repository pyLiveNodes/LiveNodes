from src.nodes.feature_avg import Feature_avg
from src.nodes.window import Window
from src.nodes.playback import Playback
from src.nodes.draw_lines import Draw_lines
from src.nodes.node import load

import numpy as np

file = "pipelines/simple.json"

print('=== Build Pipeline ====')

# TODO: currently the saving and everything else assumes we have a single node as entry, not sure if that is always true. consider multi indepdendent sensors, that are synced in the second node 
#   -> might be solveable with "pipeline nodes" or similar, where a node acts as container for a node system -> might be good for paralellisation anyway 
pl = Playback(files="./data/KneeBandageCSL2018/**/*.h5", sample_rate=1000)

# This output will not be saved, as it cannot be reconstructed
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
draw = Draw_lines(name='Raw Data', idx=idx, names=channel_names)
pl.add_output(draw)

window = Window(100, 20)
pl.add_output(window)

avg = Feature_avg()
window.add_output(avg)

draw2 = Draw_lines(name='Averaged Data', idx=idx, names=channel_names)
avg.add_output(draw2)

print('=== Save Pipeline ====')
pl.save(file)


print('=== Load Pipeline ====')
pl_val = load(file)

# TODO: validate & test pipeline
# print()

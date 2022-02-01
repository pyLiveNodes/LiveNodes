from src.nodes.biokit_norm import Biokit_norm
from src.nodes.biokit_to_fs import Biokit_to_fs
from src.nodes.biokit_from_fs import Biokit_from_fs
from src.nodes.feature_avg import Feature_avg
from src.nodes.window import Window
from src.nodes.memory import Memory
from src.nodes.playback import Playback
from src.nodes.draw_lines import Draw_lines
from src.nodes.node import Node
from src.nodes.biokit_recognizer import Biokit_recognizer
from src.nodes.draw_recognition import Draw_recognition

import numpy as np

file = "pipelines/recognize.json"

print('=== Build Pipeline ====')

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

meta = {
    "sample_rate": 1000,
    "channels": recorded_channels,
    "targets": ['cspin-ll', 'run', 'jump-2', 'shuffle-l', 'sit', 'cstep-r', 'vcut-rr', 'stair-down', 'stand-sit', 'jump-1', 'sit-stand', 'stand', 'cspin-lr', 'cspin-rr', 'cstep-l', 'vcut-ll', 'vcut-rl', 'shuffle-r', 'stair-up', 'walk', 'cspin-rl', 'vcut-lr']
}

x_raw = 10000
x_processed = 100

# TODO: currently the saving and everything else assumes we have a single node as entry, not sure if that is always true. consider multi indepdendent sensors, that are synced in the second node 
#   -> might be solveable with "pipeline nodes" or similar, where a node acts as container for a node system -> might be good for paralellisation anyway 
pl = Playback(files="./data/KneeBandageCSL2018/**/*.h5", meta=meta, batch=20)

# This output will not be saved, as it cannot be reconstructed
pl.add_output(lambda data: print(data))


idx = np.isin(recorded_channels, channel_names).nonzero()[0]
draw_raw = Draw_lines(name='Raw Data', idx=idx, names=channel_names, xAxisLength=x_raw)
pl.add_output(draw_raw)

window = Window(100, 0)
pl.add_output(window)

avg = Feature_avg()
window.add_output(avg)

draw_avg = Draw_lines(name='Averaged Data', idx=idx, names=channel_names, xAxisLength=x_processed)
avg.add_output(draw_avg)

to_fs = Biokit_to_fs()
avg.add_output(to_fs)

norm = Biokit_norm()
to_fs.add_output(norm)

from_fs = Biokit_from_fs()
norm.add_output(from_fs)

draw_normed = Draw_lines(name='Normed Data', idx=idx, names=channel_names, ylim=(-5, 5), xAxisLength=x_processed)
from_fs.add_output(draw_normed)

recog = Biokit_recognizer(model_path="./models/KneeBandageCSL2018/partition-stand/sequence/", token_insertion_penalty=50)
norm.add_output(recog)

draw_recognition_path = Draw_recognition(xAxisLength=[x_processed, x_processed, x_processed, x_raw])
recog.add_output(draw_recognition_path)
recog.add_output(draw_recognition_path, data_stream='Meta', recv_name='receive_meta')

memory = Memory(x_raw)
pl.add_output(memory, data_stream='Annotation')
memory.add_output(draw_recognition_path, recv_name='receive_annotation')


print('=== Save Pipeline ====')
pl.save(file)


print('=== Load Pipeline ====')
pl_val = Node.load(file)

# TODO: validate & test pipeline
# print()

print('=== Visualize Pipeline ====')
pl.make_dot_graph().save(file.replace('.json', '.png'))
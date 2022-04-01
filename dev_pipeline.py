import time
from src.nodes.in_playback import In_playback
from src.nodes.draw_lines import Draw_lines
from src.nodes.node import Node, Location

import numpy as np

from src.nodes.utils import logger

def _log_helper(msg):
    print(msg, flush=True)

if __name__ == '__main__':
    logger.register_cb(_log_helper)

    print('=== Construct Pipeline ====')
    # channel_names_raw = ['EMG1', 'Gonio2', 'AccLow2']
    # # channel_names_fts = ['EMG1__calc_mean', 'Gonio2__calc_mean', 'AccLow2__calc_mean']
    # channel_names_fts = ['EMG1__rms', 'Gonio2__calc_mean', 'AccLow2__calc_mean']
    # recorded_channels = [
    #     'EMG1', 'EMG2', 'EMG3', 'EMG4',
    #     'Airborne',
    #     'AccUp1', 'AccUp2', 'AccUp3',
    #     'Gonio1',
    #     'AccLow1', 'AccLow2', 'AccLow3',
    #     'Gonio2',
    #     'GyroUp1', 'GyroUp2', 'GyroUp3',
    #     'GyroLow1', 'GyroLow2', 'GyroLow3']

    # meta = {
    #     "sample_rate": 1000,
    #     "channels": recorded_channels,
    #     "targets": ['cspin-ll', 'run', 'jump-2', 'shuffle-l', 'sit', 'cstep-r', 'vcut-rr', 'stair-down', 'stand-sit', 'jump-1', 'sit-stand', 'stand', 'cspin-lr', 'cspin-rr', 'cstep-l', 'vcut-ll', 'vcut-rl', 'shuffle-r', 'stair-up', 'walk', 'cspin-rl', 'vcut-lr']
    # }

    # # pipeline = In_playback(compute_on=Location.THREAD, block=False, files="./projects/test_ask/data/KneeBandageCSL2018/**/*.h5", meta=meta)
    # pipeline = In_playback(compute_on=Location.PROCESS, block=False, files="./projects/test_ask/data/KneeBandageCSL2018/**/*.h5", meta=meta)

    # channel_names = ['Gonio2', 'GyroLow1', 'GyroLow2', 'GyroLow3']
    # idx = np.isin(recorded_channels, channel_names).nonzero()[0]

    # # draw = Draw_lines(name='Raw Data', compute_on=Location.THREAD)
    # draw = Draw_lines(name='Raw Data', compute_on=Location.PROCESS)
    # # draw = Draw_lines(name='Raw Data', compute_on=Location.SAME)
    # draw.connect_inputs_to(pipeline)


    print('=== Load Pipeline ====')
    # pipeline = Node.load('./projects/test_ask/pipelines/recognize.json')
    # pipeline = Node.load('./projects/test_ask/pipelines/preprocess_no_vis.json')
    pipeline = Node.load('./projects/test_ask/pipelines/recognize_no_vis.json')

    pipeline.start()
    time.sleep(1000)
    pipeline.stop()
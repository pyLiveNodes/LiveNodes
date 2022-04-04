import time
import numpy as np
from .node import Sender, Location
import glob, random
import h5py
import pandas as pd
import os

from .in_data import read_data

class In_playback(Sender):
    """
    Playsback previously recorded data.

    Expects the following setup variables:
    - files (str): glob pattern for files 
    - sample_rate (number): sample rate to simulate in frames per second
    - batch_size (int, default=5): number of frames that are sent at the same time -> not implemented yet
    """

    channels_in = []
    channels_out = ['Data', 'File', 'Annotation', 'Meta', 'Channel Names']

    category = "Data Source"
    description = "" 

    example_init = {'name': 'Name'}

    # TODO: consider using a file for meta data instead of dictionary...
    def __init__(self, files, meta, emit_at_once=1, annotation_holes="stand", csv_columns=["act", "start", "end"], name="Playback", compute_on=Location.THREAD, block=False, **kwargs):
        super().__init__(name, compute_on=compute_on, block=block, **kwargs)

        self.meta = meta
        self.files = files
        self.emit_at_once = emit_at_once
        self.annotation_holes = annotation_holes
        self.csv_columns = csv_columns # TODO: remove theses asap and rather convert the old datasets to a consistent format!

        self.sample_rate = meta.get('sample_rate')
        self.targets = meta.get('targets')
        self.channels = meta.get('channels')

    def _settings(self):
        return {\
            "emit_at_once": self.emit_at_once,
            "files": self.files,
            "meta": self.meta,
            "annotation_holes": self.annotation_holes,
            "csv_columns": self.csv_columns,
        }


    def _run(self):
        """
        Streams the data and calls frame callbacks for each frame.
        """
        fs = glob.glob(self.files)
        sleep_time = 1. / (self.sample_rate / self.emit_at_once)
        print(sleep_time, self.sample_rate, self.emit_at_once)
        last_time = time.time()

        target_to_id = {key: key for i, key in enumerate(self.targets)}

        self._emit_data(self.meta, channel="Meta")
        self._emit_data(self.channels, channel="Channel Names")
        ctr = -1

        if self.annotation_holes not in target_to_id:
            raise Exception('annotation filler must be in known targets. got', self.annotation_holes, target_to_id.keys())

        # TODO: add sigkill handler
        while(True):
            f = random.choice(fs)
            ctr += 1
            print(ctr, f)


            # Read and send data from file
            with h5py.File(f, "r") as dataFile:
                dataSet = dataFile.get("data")
                start = 0
                end = len(dataSet)
                data = dataSet[start:end] # load into mem

                # Prepare framewise annotation to be send
                targs = []
                if os.path.exists(f.replace('.h5', '.csv')):
                    ref = pd.read_csv(f.replace('.h5', '.csv'), names=self.csv_columns)
                    j = 0
                    for _, row in ref.iterrows():
                        # This is hacky af, but hey... achieves that we cann playback annotaitons with holes (and fill those) and also playback annotations without holes
                        if self.annotation_holes in target_to_id:
                            targs += [target_to_id[self.annotation_holes]] * (row['start'] - j) # use stand as filler for unknown. #Hack! TODO: remove
                        targs += [target_to_id[row['act'].strip()]] * (row['end'] - row['start'])
                        j = row['end']
                    if self.annotation_holes in target_to_id:
                        targs += [target_to_id[self.annotation_holes]] * (len(data) - j)

                # TODO: for some reason i have no fucking clue about using read_data results in the annotation plot in draw recog to be wrong, although the targs are exactly the same (yes, if checked read_data()[1] == targs)...
                for i in range(start, end, self.emit_at_once):
                    d_len = len(data[i:i+self.emit_at_once]) # usefull if i+self.emit_at_once > len(data), as then all the rest will be read into one batch
                    
                    # if d_len < self.emit_at_once:
                    #     print('Interesting')
                    # The data format is always: (batch/file, time, channel)
                    # self.debug(data[i:i+self.emit_at_once][0])
                    self._emit_data(np.array([data[i:i+self.emit_at_once]]))

                    if len(targs[i:i+self.emit_at_once]) > 0:
                        # use reshape -1, as the data can also be shorter than emit_at_once and will be adjusted accordingly
                        self._emit_data(np.array(targs[i:i+self.emit_at_once]).reshape((1, -1, 1)), channel='Annotation')
                    
                    self._emit_data(np.array([ctr] * d_len).reshape((1, -1, 1)), channel="File")
                    
                    while time.time() < last_time + sleep_time:
                        time.sleep(0.00001)

                    last_time = time.time()

                    yield True
        yield False

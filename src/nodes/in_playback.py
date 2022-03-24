import time
import numpy as np
from .node import Sender
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
    # - batch_size (int, default=5): number of frames that are sent at the same time -> not implemented yet
    """

    channels_in = []
    channels_out = ['Data', 'File', 'Annotation', 'Meta', 'Channel Names']

    category = "Data Source"
    description = "" 

    example_init = {'name': 'Name'}

    # TODO: consider using a file for meta data instead of dictionary...
    def __init__(self, files, meta, batch=1, annotation_holes="Stand", csv_columns=["act", "start", "end"], name="Playback", **kwargs):
        super().__init__(name, **kwargs)

        self.meta = meta
        self.files = files
        self.batch = batch
        self.annotation_holes = annotation_holes
        self.csv_columns = csv_columns # TODO: remove theses asap and rather convert the old datasets to a consistent format!

        self.sample_rate = meta.get('sample_rate')
        self.targets = meta.get('targets')
        self.channels = meta.get('channels')

    def _settings(self):
        return {\
            "batch": self.batch,
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
        sleep_time = 1. / (self.sample_rate / self.batch)
        print(sleep_time, self.sample_rate, self.batch)

        target_to_id = {key: key for i, key in enumerate(self.targets)}

        self._emit_data(self.meta, channel="Meta")
        self._emit_data(self.channels, channel="Channel Names")
        ctr = -1

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

                for i in range(start, end, self.batch):
                    d_len = len(data[i:i+self.batch]) # usefull if i+self.batch > len(data)
                    self._emit_data(np.array(data[i:i+self.batch]))
                    if len(targs[i:i+self.batch]) > 0:
                        self._emit_data(targs[i:i+self.batch], channel='Annotation')
                    self._emit_data([ctr] * d_len, channel="File")
                    
                    time.sleep(sleep_time)
                    yield True
        yield False

        # TODO: look at this implementation again, seems to be the more precise one
        # samples_per_frame = int(self.sample_rate / 1000 * self.frame_size_ms)
        # time_val = time.time()
        # time_val_init = time_val
        # for sample_cnt in range(0, len(self.data), samples_per_frame):
        #     samples = self.data[sample_cnt:sample_cnt+samples_per_frame]
        #     # if not self.asap:
        #     while time.time() - time_val < (1.0 / 1000.0) * self.frame_size_ms:
        #         time.sleep(0.000001)
        #     time_val = time_val_init + sample_cnt / self.sample_rate
        #     self._emit_data(np.array(samples))
    
from functools import reduce
import numpy as np
from glob import glob
import h5py
import pandas as pd
import random
from joblib import Parallel, delayed

from livenodes.core.sender import Sender

def read_data(f):
    try:
        # Read and send data from file
        with h5py.File(f, "r") as dataFile:
            dataSet = dataFile.get("data")
            data = dataSet[:]  # load into mem

            # Prepare framewise annotation to be send
            ref = pd.read_csv(f.replace('.h5', '.csv'))
            
            # @deprecated (old format, that used to have holes, where no annotation was present)
            targs = []
            last_end = 0
            for _, row in ref.iterrows():
                filler = "None"  # use stand as filler for unknown. #Hack! TODO: remove
                targs.append([filler] * (row['start'] - last_end))
                # +1 as the numbers are samples, ie the last sample still has that label
                targs.append([row['act']] * (row['end'] - row['start'])) # +1 as the numbers are samples, ie the last sample still has that label
                last_end = row['end']
            targs.append([filler] * (len(data) - last_end))
            targs = list(np.concatenate(targs))

        return data, targs
    except (OSError, TypeError):
        print('Could not open file, skipping', f)
        return [], []


from . import local_registry


@local_registry.register
class In_data(Sender):
    """
    Playsback previously recorded data.

    Expects the following setup variables:
    - files (str): glob pattern for files 
    - sample_rate (number): sample rate to simulate in frames per second
    # - emit_at_once_size (int, default=5): number of frames that are sent at the same time -> not implemented yet
    """

    channels_in = []
    channels_out = [
        'Data', 'File', 'Annotation', 'Meta', 'Channel Names', 'Percent'
    ]

    category = "Data Source"
    description = ""

    example_init = {
        "files": "./files/**.h5",
        "files_exclude": './files/part0*.h5',
        "meta": {
            "sample_rate": 100,
            "targets": ["target 1"],
            "channels": ["Channel 1"]
        },
        "shuffle": True,
        "emit_at_once": 1,
        "name": "Data input",
    }

    # TODO: consider using a file for meta data instead of dictionary...
    def __init__(self,
                 files,
                 meta,
                 files_exclude = '',
                 shuffle=True,
                 emit_at_once=1,
                 name="Data input",
                 **kwargs):
        super().__init__(name, **kwargs)

        self.meta = meta
        self.files = files
        self.files_exclude = files_exclude
        self.emit_at_once = emit_at_once
        self.shuffle = shuffle

        self.sample_rate = meta.get('sample_rate')
        self.targets = meta.get('targets')
        self.channels = meta.get('channels')

    def _settings(self):
        return {\
            "emit_at_once": self.emit_at_once,
            "files": self.files,
            "files_exclude": self.files_exclude,
            "meta": self.meta,
            "shuffle": self.shuffle
        }

    def _run(self):
        """
        Streams the data and calls frame callbacks for each frame.
        """
        fs = sorted(list(set(glob(self.files)) - set(glob(self.files_exclude))))

        if self.shuffle:
            random.shuffle(fs)

        self.info('Reading these files (in this order):', fs)

        self._emit_data(self.meta, channel="Meta")
        self._emit_data(self.channels, channel="Channel Names")

        # TODO: create a producer/consumer (blocking)queue (with fixed items) here for best of both worlds ie fixed amount of mem with no hw access delay
        # for now: just preload everything
        in_mem = Parallel(n_jobs=10)(delayed(read_data)(f) for f in fs)
        in_mem = list(filter(lambda x: len(x[0]), in_mem)) # Remove all empty lists from when we couldn't open files

        sent_samples = 0
        total_n_samples = reduce(lambda cur, nxt: cur + len(nxt[1]), in_mem, 0)

        for file_number, (f, (data, targs)) in enumerate(zip(fs, in_mem)):
            for i in range(0, len(data), self.emit_at_once):
                # usefull if i+self.emit_at_once > len(data)
                d_len = len(data[i:i + self.emit_at_once])  
                sent_samples += d_len

                self._emit_data(np.array([data[i:i + self.emit_at_once]]))
                
                # use reshape -1, as the data can also be shorter than emit_at_once and will be adjusted accordingly
                self._emit_data(np.array(
                targs[i:i + self.emit_at_once]).reshape((1, -1, 1)),
                                channel='Annotation')
                
                self._emit_data(np.array([file_number] * d_len).reshape(
                    (1, -1, 1)),
                                channel="File")

                self._emit_data(sent_samples / total_n_samples, channel='Percent')  

                finished = sent_samples >= total_n_samples
                self.info('finished?', not finished)
                yield not finished

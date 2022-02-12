import time
import numpy as np
from multiprocessing import Process
import threading
from .node import Node
import glob, random
import h5py
import pandas as pd
import random

from joblib import Parallel, delayed

from .utils import printProgressBar


def read_data(f):
    # Read and send data from file
    with h5py.File(f, "r") as dataFile:
        dataSet = dataFile.get("data")
        data = dataSet[:] # load into mem

        # Prepare framewise annotation to be send
        ref = pd.read_csv(f.replace('.h5', '.csv'), names=["act", "start", "end"])
        targs = []
        last_end = 0
        for _, row in ref.iterrows():
            filler = "stand" # use stand as filler for unknown. #Hack! TODO: remove
            targs.append([filler] * (row['start'] - last_end))
            targs.append([row['act']] * (row['end'] - row['start']))
            last_end = row['end']
        targs.append([filler] * (len(data) - last_end))
        targs = list(np.concatenate(targs))

    return data, targs


class In_data(Node):
    """
    Playsback previously recorded data.

    Expects the following setup variables:
    - files (str): glob pattern for files 
    - sample_rate (number): sample rate to simulate in frames per second
    # - batch_size (int, default=5): number of frames that are sent at the same time -> not implemented yet
    """
    # TODO: consider using a file for meta data instead of dictionary...
    def __init__(self, files, meta, shuffle=True, batch=1, name="Data input", dont_time=False):
        super().__init__(name, has_inputs=False, dont_time=dont_time)
        self.feeder_process = None

        self.meta = meta
        self.files = files
        self.batch = batch
        self.shuffle = shuffle

        self.sample_rate = meta.get('sample_rate')
        self.targets = meta.get('targets')
        self.channels = meta.get('channels')

        self._stop_event = threading.Event()
    
    def _get_setup(self):
        return {\
            "batch": self.batch,
            "files": self.files,
            "meta": self.meta,
            "shuffle": self.shuffle
        }

    def stop(self):
        self._stop_event.set()
        # self.feeder_process.terminate()

    def sender_process(self):
        """
        Streams the data and calls frame callbacks for each frame.
        """
        fs = glob.glob(self.files)

        if self.shuffle:
            random.shuffle(fs)

        self.send_data(self.meta, data_stream="Meta")
        self.send_data(self.channels, data_stream="Channel Names")

        # TODO: create a producer/consumer queue here for best of both worlds ie fixed amount of mem with no hw access delay
        # for now: just preload everything
        in_mem = Parallel(n_jobs=10)(delayed(read_data)(f) for f in fs)

        l = len(fs)
        printProgressBar(0, l, prefix = 'Progress:', suffix = '', length = 50)
        for file_number, (f, (data, targs)) in enumerate(zip(fs, in_mem)):
        # for file_number, f in enumerate(fs):
            printProgressBar(file_number, l, prefix = 'Progress:', suffix = f, length = 50)

            # data, targs = read_data(f)
                
            for i in range(0, len(data), self.batch):
                d_len = len(data[i:i+self.batch])
                self.send_data(data[i:i+self.batch])
                self.send_data(targs[i:i+self.batch], data_stream='Annotation')
                self.send_data([file_number] * d_len, data_stream="File")

        self.send_data(None, data_stream='Termination') # TODO: maybe we could use something like this for syncing... ie seperate stream with just a counter 
    
    def start_processing(self, recurse=True):
        """
        Starts the streaming process.
        """
        if self.feeder_process is None:
            self.feeder_process = threading.Thread(target=self.sender_process)
            # self.feeder_process = Process(target=self.sender_process)
            self.feeder_process.start()
        super().start_processing(recurse)
        
    def stop_processing(self, recurse=True):
        """
        Stops the streaming process.
        """
        super().stop_processing(recurse)
        if self.feeder_process is not None:
            self.stop()
        self.feeder_process = None
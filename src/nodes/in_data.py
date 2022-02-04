import time
import numpy as np
from multiprocessing import Process
import threading
from .node import Node
import glob, random
import h5py
import pandas as pd
import random

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

    def sender_process(self):
        """
        Streams the data and calls frame callbacks for each frame.
        """
        fs = glob.glob(self.files)

        if self.shuffle:
            random.shuffle(fs)

        target_to_id = {key: key for i, key in enumerate(self.targets)}

        self.send_data(self.meta, data_stream="Meta")
        self.send_data(self.channels, data_stream="Channel Names")

        for i, f in enumerate(fs):
            print(f)

            # Prepare framewise annotation to be send
            ref = pd.read_csv(f.replace('.h5', '.csv'), names=["act", "start", "end"])
            targs = []
            j = 0
            for _, row in ref.iterrows():
                targs += [target_to_id["stand"]] * (row['start'] - j) # use stand as filler for unknown. #Hack! TODO: remove
                targs += [target_to_id[row['act']]] * (row['end'] - row['start'] - j)
                j = row['end']

            # Read and send data from file
            with h5py.File(f, "r") as dataFile:
                dataSet = dataFile.get("data")
                data = dataSet[:] # load into mem
                
                for i in range(0, len(data), self.batch):
                    self.send_data(np.array(data[i:i+self.batch]))
                    self.send_data(targs[i:i+self.batch], data_stream='Annotation')
                    self.send_data([i] * self.batch, data_stream="File")
        self.send_data(None, data_stream='Termination') # TODO: maybe we could use something like this for syncing... ie seperate stream with just a counter 
    
    def start_processing(self, recurse=True):
        """
        Starts the streaming process.
        """
        if self.feeder_process is None:
            self.feeder_process = threading.Thread(target=self.sender_process)
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
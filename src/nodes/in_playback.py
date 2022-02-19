import time
import numpy as np
from multiprocessing import Process
import threading
from .node import Node
import glob, random
import h5py
import pandas as pd
import os

from .in_data import read_data

class In_playback(Node):
    """
    Playsback previously recorded data.

    Expects the following setup variables:
    - files (str): glob pattern for files 
    - sample_rate (number): sample rate to simulate in frames per second
    # - batch_size (int, default=5): number of frames that are sent at the same time -> not implemented yet
    """
    # TODO: consider using a file for meta data instead of dictionary...
    def __init__(self, files, meta, batch=1, name="Playback", dont_time=False):
        super().__init__(name, has_inputs=False, dont_time=dont_time)
        self.feeder_process = None

        self.meta = meta
        self.files = files
        self.batch = batch

        self.sample_rate = meta.get('sample_rate')
        self.targets = meta.get('targets')
        self.channels = meta.get('channels')

        self._stop_event = threading.Event()
    
    @staticmethod
    def info():
        return {
            "class": "In_playback",
            "file": "In_playback.py",
            "in": [],
            "out": ["Data", "File", "Annotation", "Meta", "Channel Names"],
            "init": {}, #TODO!
            "category": "Data Source"
        }

    def _get_setup(self):
        return {\
            "batch": self.batch,
            "files": self.files,
            "meta": self.meta
        }

    def stop(self):
        self._stop_event.set()
        # self.feeder_process.terminate()

    def sender_process(self):
        """
        Streams the data and calls frame callbacks for each frame.
        """
        fs = glob.glob(self.files)
        sleep_time = 1. / (self.sample_rate / self.batch)
        print(sleep_time, self.sample_rate, self.batch)

        target_to_id = {key: key for i, key in enumerate(self.targets)}

        self.send_data(self.meta, data_stream="Meta")
        self.send_data(self.channels, data_stream="Channel Names")
        ctr = -1

        while(not self._stop_event.is_set()):
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
                    ref = pd.read_csv(f.replace('.h5', '.csv'), names=["act", "start", "end"])
                    j = 0
                    for _, row in ref.iterrows():
                        targs += [target_to_id["stand"]] * (row['start'] - j) # use stand as filler for unknown. #Hack! TODO: remove
                        targs += [target_to_id[row['act']]] * (row['end'] - row['start'])
                        j = row['end']
                    targs += [target_to_id["stand"]] * (len(data) - j)

                # TODO: for some reason i have no fucking clue about using read_data results in the annotation plot in draw recog to be wrong, although the targs are exactly the same (yes, if checked read_data()[1] == targs)...

                for i in range(start, end, self.batch):
                    d_len = len(data[i:i+self.batch]) # usefull if i+self.batch > len(data)
                    self.send_data(np.array(data[i:i+self.batch]))
                    if len(targs[i:i+self.batch]) > 0:
                        self.send_data(targs[i:i+self.batch], data_stream='Annotation')
                    self.send_data([ctr] * d_len, data_stream="File")
                    time.sleep(sleep_time)

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
        #     self.send_data(np.array(samples))
    
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
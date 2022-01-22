import time
import numpy as np
from multiprocessing import Process
import threading
from .node import Node
import glob, random
import h5py
import pandas as pd

class Playback(Node):
    """
    Playsback previously recorded data.

    Expects the following setup variables:
    - files (str): glob pattern for files 
    - sample_rate (number): sample rate to simulate in frames per second
    # - batch_size (int, default=5): number of frames that are sent at the same time -> not implemented yet
    """
    def __init__(self, files, sample_rate, batch=1, name="Playback", dont_time=False):
        super().__init__(name, has_inputs=False, dont_time=dont_time)
        self.feeder_process = None

        self.sample_rate = sample_rate
        self.files = files
        self.batch = batch

        self._stop_event = threading.Event()
    
    def _get_setup(self):
        return {\
            "batch": self.batch,
            "files": self.files,
            "sample_rate": self.sample_rate
        }

    def stop(self):
        self._stop_event.set()
        
    def sender_process(self):
        """
        Streams the data and calls frame callbacks for each frame.
        """
        fs = glob.glob(self.files)
        sleep_time = 1. / (self.sample_rate / self.batch)
        # print(sleep_time, self.sample_rate, self.batch)

        while(not self._stop_event.is_set()):
            f = random.choice(fs)
            # print(f)
            # ref = pd.read_csv(f.replace('.h5', '.csv'), names=["act", "start", "end"])
            # targs = []
            # j = 0
            # for _, row in ref.iterrows():
            #     targs += [self.target_to_id["stand"]] * (row['start'] - j)
            #     targs += [self.target_to_id[row['act']]] * (row['end'] - row['start'] - j)
            #     j = row['end']

            with h5py.File(f, "r") as dataFile:
                dataSet = dataFile.get("data")
                start = 0
                end = len(dataSet)
                data = dataSet[start:end] # load into mem
                
                for i in range(start, end, self.batch):
                    # self.add_data(np.array(data[i:i+self.batch]))
                    self.add_data(np.array([data[i]]))
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
        #     self.output_data(np.array(samples))
    
    def start_processing(self, recurse=True):
        """
        Starts the streaming process.
        """
        if self.feeder_process is None:
            # TODO: figure out why the Process results in no data being plotted
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
            # self.feeder_process.terminate()
        self.feeder_process = None
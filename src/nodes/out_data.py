import time
import numpy as np
from multiprocessing import Process
import threading
from .node import Node
import glob, random
import h5py
import pandas as pd
import random

class Out_data(Node):
    """
    Playsback previously recorded data.

    Expects the following setup variables:
    - file (str): glob pattern for files 
    - sample_rate (number): sample rate to simulate in frames per second
    # - batch_size (int, default=5): number of frames that are sent at the same time -> not implemented yet
    """
    # TODO: consider using a file for meta data instead of dictionary...
    def __init__(self, file, name="Data input", dont_time=False):
        super().__init__(name, has_outputs=False, dont_time=dont_time)
        self.feeder_process = None

        # TODO: change this to folder instead? might make in and out easier compatible as we can have more assumptions about the data formats etc
        self.file = file

        self.outputFile = h5py.File(self.outputFilename + '.h5', 'w')
        self.outputDataset = self.outputFile.create_dataset ("data", (1, len(self.recorded_channels)), maxshape = (None, len(self.recorded_channels)), dtype = "float32")
       
    
    def _get_setup(self):
        return {\
            "file": self.file
        }

    ### TODO: implement and test this!

    def sender_process(self):
        """
        Streams the data and calls frame callbacks for each frame.
        """
        fs = glob.glob(self.file)

        if self.shuffle:
            random.shuffle(fs)

        target_to_id = {key: key for i, key in enumerate(self.targets)}

    #     self.send_data(self.meta, data_stream="Meta")
    #     self.send_data(self.channels, data_stream="Channel Names")

    #     for f in fs:
    #         print(f)

    #         # Prepare framewise annotation to be send
    #         ref = pd.read_csv(f.replace('.h5', '.csv'), names=["act", "start", "end"])
    #         targs = []
    #         j = 0
    #         for _, row in ref.iterrows():
    #             targs += [target_to_id["stand"]] * (row['start'] - j) # use stand as filler for unknown. #Hack! TODO: remove
    #             targs += [target_to_id[row['act']]] * (row['end'] - row['start'] - j)
    #             j = row['end']

    #         # Read and send data from file
    #         with h5py.File(f, "r") as dataFile:
    #             dataSet = dataFile.get("data")
    #             data = dataSet[:] # load into mem
                
    #             for i in range(0, len(data), self.batch):
    #                 self.send_data(np.array(data[i:i+self.batch]))
    #                 self.send_data(targs[i:i+self.batch], data_stream='Annotation')
    
    # def receive_data(self, data_frame, **kwargs):
    #     return super().receive_data(data_frame, data_id, **kwargs)()

    # def start_processing(self, recurse=True):
    #     """
    #     Starts the streaming process.
    #     """
    #     if self.feeder_process is None:
    #         self.feeder_process = threading.Thread(target=self.sender_process)
    #         self.feeder_process.start()
    #     super().start_processing(recurse)
        
    # def stop_processing(self, recurse=True):
    #     """
    #     Stops the streaming process.
    #     """
    #     super().stop_processing(recurse)
    #     if self.feeder_process is not None:
    #         self.stop()
    #     self.feeder_process = None
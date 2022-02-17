import time
import datetime
import numpy as np
from multiprocessing import Process
import threading
from .node import Node
import glob, random
import h5py
import pandas as pd
import random
import json
import os
import multiprocessing as mp


class Out_data(Node):
    """
    Playsback previously recorded data.

    Expects the following setup variables:
    - file (str): glob pattern for files 
    - sample_rate (number): sample rate to simulate in frames per second
    # - batch_size (int, default=5): number of frames that are sent at the same time -> not implemented yet
    """
    # TODO: consider using a file for meta data instead of dictionary...
    def __init__(self, folder, name="Data input", dont_time=False):
        super().__init__(name, has_outputs=False, dont_time=dont_time)
        self.feeder_process = None

        # TODO: change this to folder instead? might make in and out easier compatible as we can have more assumptions about the data formats etc
        self.folder = folder

        self.outputFilename = f"{name}/{datetime.datetime.fromtimestamp(time.time())}"

        self.outputFile = h5py.File(self.outputFilename + '.h5', 'w')
        self.outputDataset = None
        self._wait_queue = mp.Queue()

       
    @staticmethod
    def info():
        return {
            "class": "out_data",
            "file": "out_data.py",
            "in": ["Data", "Channel Names", "Meta"],
            "out": [],
            "init": {}, #TODO!
            "category": "Save"
        }
    
    @property
    def in_map(self):
        return {
            "Data": self.receive_data,
            "Channel Names": self.receive_channels
        }

    
    def _get_setup(self):
        return {\
            "folder": self.folder
        }

    def receive_data(self, data_frame, **kwargs):
        if self.outputDataset is None:
            self._wait_queue.put(data_frame)

            # Assume that we don't have any changes in the channels over time
            if self.channels is not None:
                self.outputDataset = self.outputFile.create_dataset("data", (1, len(self.channels)), maxshape = (None, len(self.channels)), dtype = "float32")
        else:
            self.outputDataset.extend(data_frame)

    def _read_meta(self):
        if not os.path.exists(self.outputFilename):
            return {}
        with open(self.outputFilename, 'r') as f:
            return json.load(f) 
    
    def _write_meta(self, setting):
        with open(self.outputFilename, 'w') as f:
            json.dump(setting, f, indent=2) 

    def receive_channels(self, channels, **kwargs):
        self.channels = channels

        m_dict = self._read_meta()
        m_dict['channels'] = channels
        self._write_meta(m_dict)

    def receive_meta(self, meta, **kwargs):
        m_dict = self._read_meta()
        for key, val in meta.items():
            # We'll assume that the channels are always hooked up
            if not (key == "channels"):
                m_dict[key] = val
        self._write_meta(m_dict)
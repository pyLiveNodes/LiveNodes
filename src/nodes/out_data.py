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
    # # TODO: FIX THIS! This is a problem as soon as we have mor than one output!
    # outputDataset = None
    # outputFile = None

    """
    Playsback previously recorded data.

    Expects the following setup variables:
    - file (str): glob pattern for files 
    - sample_rate (number): sample rate to simulate in frames per second
    # - batch_size (int, default=5): number of frames that are sent at the same time -> not implemented yet
    """
    # TODO: consider using a file for meta data instead of dictionary...
    def __init__(self, folder, name="Save", dont_time=False):
        super().__init__(name, has_outputs=False, dont_time=dont_time)

        self.folder = folder

        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

        # NOTE: we can create the filename here (although debatable)
        # but we cannot create the file here, as no processing is being done or even planned yet (this might just be create_pipline)
        self.outputFilename = f"{self.folder}{datetime.datetime.fromtimestamp(time.time())}"
        print("Saving to:", self.outputFilename)

        self.outputFile = None
        self.outputDataset = None
        self._wait_queue = mp.Queue()

        self.outputFileAnnotation = None
        self.last_annotation = None
       
    @staticmethod
    def info():
        return {
            "class": "Out_data",
            "file": "Out_data.py",
            "in": ["Data", "Channel Names", "Meta", "Annotation"],
            "out": [],
            "init": {
                "name": "Save",
                "folder": "./data/Debug/"
            },
            "category": "Save"
        }
    
    @property
    def in_map(self):
        return {
            "Data": self.receive_data,
            "Channel Names": self.receive_channels,
            "Meta": self.receive_meta,
            "Annotation": self.receive_annotation,
        }

    
    def _get_setup(self):
        return {\
            "folder": self.folder
        }

    def receive_data(self, data_frame, **kwargs):
        if self.outputDataset is None:
            self._wait_queue.put(data_frame)

            # Assume that we don't have any changes in the channels over time
            if self.channels is not None and self.outputFile is not None:
                self.outputDataset = self.outputFile.create_dataset("data", (1, len(self.channels)), maxshape = (None, len(self.channels)), dtype = "float32")
        else:
            # feels weird, but i haven't found an extend or append api
            self.outputDataset.resize(self.outputDataset.shape[0] + len(data_frame), axis = 0)
            self.outputDataset[-len(data_frame):] = data_frame

    def receive_annotation(self, data_frame, **kwargs):
        # For now lets assume the file is always open before this is called.
        # TODO: re-consider that assumption
        if self.last_annotation is None:
            self.last_annotation = (data_frame[0], 0, 0)
        
        for annotation in data_frame:
            if annotation == self.last_annotation[0]:
                self.last_annotation = (annotation, self.last_annotation[1], self.last_annotation[2] + 1)
            else:
                self.outputFileAnnotation.write(f"{self.last_annotation[1]},{self.last_annotation[2]},{self.last_annotation[0]}\n")
                self.last_annotation = (annotation, self.last_annotation[2] + 1, self.last_annotation[2] + 1)



    def start_processing(self, recurse=True):
        """
        Starts the streaming process.
        """
        if self.outputFile is None:
            self.outputFile = h5py.File(self.outputFilename + '.h5', 'w')
            self.outputFileAnnotation = open(f"{self.outputFilename}.csv", "w")
        super().start_processing(recurse)
        
    def stop_processing(self, recurse=True):
        """
        Stops the streaming process.
        """
        super().stop_processing(recurse)
        if self.outputFile is not None:
            self.outputFile.close()
            if self.last_annotation is not None:
                self.outputFileAnnotation.write(f"{self.last_annotation[1]},{self.last_annotation[2]},{self.last_annotation[0]}")
            self.outputFileAnnotation.close()
            print('Stopped Writing out')
        self.outputFile = None
        self.outputDataset = None
        self.outputFileAnnotation = None


    def _read_meta(self):
        if not os.path.exists(f"{self.outputFilename}.json"):
            return {}
        with open(f"{self.outputFilename}.json", 'r') as f:
            return json.load(f) 
    
    def _write_meta(self, setting):
        with open(f"{self.outputFilename}.json", 'w') as f:
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
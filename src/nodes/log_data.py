import time
import numpy as np
from multiprocessing import Process
import threading
from .node import Node
import glob, random
import h5py
import pandas as pd
import random

class Log_data(Node):
    @staticmethod
    def info():
        return {
            "class": "Log_data",
            "file": "Log_data.py",
            "in": ["Data"],
            "out": ["Data"],
            "init": {}, #TODO!
            "category": "Basic"
        }

    def receive_data(self, data_frame, **kwargs):
        print(data_frame)
        self.send_data(data_frame)
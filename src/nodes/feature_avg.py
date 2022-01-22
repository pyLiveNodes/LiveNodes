import time
import numpy as np
from multiprocessing import Process
import threading
from .node import Node
import glob, random
import h5py
import pandas as pd
import matplotlib.pyplot as plt

# TODO: rather use the same mechanism as in the mkr library so that all features can be added at once
class Feature_avg(Node):
    def add_data(self, data_frame, data_id=0):
        # print(np.array(data_frame).shape, np.mean(data_frame, axis=0).shape)
        self.output_data([np.mean(data_frame, axis=0)])

import collections
from queue import Queue
from tkinter import N
import numpy as np

from .node import Node

import matplotlib.patches as mpatches

import multiprocessing as mp
import ctypes as c

import time

# The draw pattern works as follows:
# 1. init_draw is called externally by matplotlib or qt and provides access to the subfig. 
#   -> use this to setup axes, paths etc
# 2. init_draw returns a update function which is also called externally and does not receive any inputs
#   -> this should only interface the update calls on matplotlib using data stored in the attributes of the class instance
# 3. receive_data is called by the pipeline and receives the data as well as potential meta information or other data channels
#   -> calculate the data you will render in the update fn from draw_init
#
# The main advantage of this is, that the pipeline and render loops are separated and one doesn't slow down the other
#  


class Draw_scatter(Node):
    # TODO: move the sample rate into a data_stream?
    def __init__(self, ylim=(-1.1, 1.1), xlim=(-1.1, 1.1), name = "Draw Output Lines", dont_time = False):
        super().__init__(name=name, has_outputs=False, dont_time=dont_time)
        self.ylim = ylim
        self.xlim = xlim

        # data generation process
        self.data_queue = mp.SimpleQueue()
        self.name_queue = mp.SimpleQueue()

    @staticmethod
    def info():
        return {
            "class": "Draw_lines",
            "file": "draw_lines.py",
            "in": ["Data", "Channel Names"],
            "out": [],
            "init": {
                "name": "Name"
            },
            "category": "Draw"
        }
        
    @property
    def in_map(self):
        return {
            "Data": self.receive_data,
            "Channel Names": self.receive_channels
        }

    def _get_setup(self):
        return {\
            "name": self.name,
            "n_plots": self.n_plots, # TODO: consider if we could make this max_plots so that the data stream might also contain less than the specified amount of plots
            "xAxisLength": self.xAxisLength,
            "sample_rate": self.sample_rate,
            "ylim": self.ylim
           }

    def init_draw(self, subfig):
        subfig.suptitle(self.name, fontsize=14)

        self.ax = subfig.subplots(1, 1)
        self.ax.set_xlim(-2.1, 2.1)
        self.ax.set_ylim(-2.1, 2.1)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)

        xData = [0] * self.n_scatter_points 
        yData = [0] * self.n_scatter_points
        alphas = np.linspace(0.1, 1, self.n_scatter_points)

        scatter = self.ax.scatter(xData, yData, alpha=alphas)

        # this way all the draw details are hidden from everyone else
        # TODO: make this expect python/numpy arrays instead of biokit 
        def update(**kwargs):
            nonlocal xData, yData # no clue why this is needed here, but not the draw and update funcitons...

            processedData = self._empty_queue(self.queue_data)
            # channel_names = self._empty_queue(self.queue_channels)

            if processedData != None:
                processedMcfs = processedData.getMatrix().T[self.idx] # just use the first two, filter does change the order of the channels, so that should be used if specific channels shall be plotted
                xData.extend(processedMcfs[0])
                xData = xData[-(self.n_scatter_points + 1):]
                yData.extend(processedMcfs[1])
                yData = yData[-(self.n_scatter_points + 1):]

                data = np.hstack((np.array(xData)[:,np.newaxis], np.array(yData)[:, np.newaxis]))
                scatter.set_offsets(data)
            return [scatter]
        return update

    def receive_channels(self, names, **kwargs):
        self.name_queue.put(names)

    def receive_data(self, data, **kwargs):
        self.queue_data.put(data)

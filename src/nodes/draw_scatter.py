import collections
from queue import Queue
from tkinter import N
import numpy as np

from .node import Node

import matplotlib.patches as mpatches

import multiprocessing as mp
import ctypes as c

import time


class Draw_scatter(Node):
    channels_in = ['Data', 'Channel Names']
    channels_out = []

    category = "Draw"
    description = "" 

    example_init = {
        "name": "Draw Data Scatter",
        "n_scatter_points": 5000,
        "ylim": (-1.1, 1.1)
    }

    # TODO: move the sample rate into a data_stream?
    def __init__(self, n_scatter_points=5000, ylim=(-1.1, 1.1), name = "Draw Output Scatter", **kwargs):
        super().__init__(name=name, **kwargs)

        self.n_scatter_points = n_scatter_points
        self.ylim = ylim

        # computation process
        # yData follows the structure (time, channel)
        self.data = np.zeros(n_scatter_points * 2).reshape((n_scatter_points, 2))

        # render process
        self.channel_names = list(map(str, range(2)))

    def _settings(self):
        return {\
            "name": self.name,
            "n_scatter_points": self.n_scatter_points,
            "ylim": self.ylim
           }

    def _init_draw(self, subfig):
        subfig.suptitle(self.name, fontsize=14)

        ax = subfig.subplots(1, 1)
        ax.set_xlim(-0.5, 0.5)
        ax.set_ylim(-0.5, 0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # ax.set_xlabel(self.plot_names[0])
        # ax.set_ylabel(self.plot_names[1])

        alphas = np.linspace(0.1, 1, self.n_scatter_points)
        xData = self.data[:, 0]
        yData = self.data[:, 1]

        scatter = ax.scatter(xData, yData, alpha=alphas)

        # self.labels = [ax.text(0.005, 0.95, name, zorder=100, fontproperties=ax.xaxis.label.get_font_properties(), rotation='horizontal', va='top', ha='left', transform = ax.transAxes) for name, ax in zip(self.channel_names, axes)]

        def update (data, channel_names):
            nonlocal self
            # Not sure why the changes part doesn't work, (not even with zorder)
            # -> could make stuff more efficient, but well...
            # changes = []

            # if self.channel_names != channel_names:
            #     self.channel_names = channel_names

            #     for i, label in enumerate(self.labels):
            #         label.set_text(self.channel_names[i])

            xData = data[:, 0]
            yData = data[:, 1]

            data = np.hstack((np.array(xData)[:,np.newaxis], np.array(yData)[:, np.newaxis]))
            scatter.set_offsets(data)

            return [scatter]

        return update


    def _should_process(self, data=None, channel_names=None):
        return data is not None and (self.channel_names is not None or channel_names is not None)

    # data should follow the (batch/file, time, channel) format
    def process(self, data, channel_names=None):
        if channel_names is not None:
            self.channel_names = channel_names

        # if (batch/file, time, channel)
        # d = np.vstack(np.transpose(data, (0, -1, -2)))
        
        # currently this is still (time, channel)
        d = np.vstack(np.array(data)[:, :2])
        # self._log(np.array(data).shape, d.shape, self.yData.shape)

        self.data = np.roll(self.data, d.shape[0], axis=0)
        self.data[:d.shape[0]] = d

        # TODO: consider if we really always want to send the channel names? -> seems an unecessary overhead (but cleaner code atm, maybe massage later...)
        self._emit_draw(data=list(self.data[:self.n_scatter_points].T), channel_names=self.channel_names)







    # TODO: move the sample rate into a data_stream?
    def __init__(self, ylim=(-1.1, 1.1), xlim=(-1.1, 1.1), name = "Draw Output Scatter", **kwargs):
        super().__init__(name=name, **kwargs)
        self.ylim = ylim
        self.xlim = xlim

        # data generation process
        self.data_queue = mp.SimpleQueue()
        self.name_queue = mp.SimpleQueue()


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

            processedData = self._empty_queue(self.data_queue)
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

    def process(self, data, **kwargs):
        self.data_queue.put(data)

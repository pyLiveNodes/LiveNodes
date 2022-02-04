import collections
from queue import Queue
from tkinter import N
import numpy as np

from .blit import BlitManager
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


class Draw_lines(Node):
    # TODO: consider removing the filter here and rather putting it into a filter node
    def __init__(self, n_plots=4, xAxisLength=5000, ylim=(-1.1, 1.1), name = "Draw Output Lines", dont_time = False):
        super().__init__(name=name, has_outputs=False, dont_time=dont_time)
        self.xAxisLength = xAxisLength
        self.ylim = ylim
        self.n_plots = n_plots

        # render process
        self.yData = [[0] * self.xAxisLength] * n_plots
        # data generation process
        self.data_queue = mp.SimpleQueue()
        self.name_queue = mp.SimpleQueue()

        self.names = list(map(str, range(n_plots)))
        # self.axes = []

    def _get_setup(self):
        return {\
            "name": self.name,
            "n_plots": self.n_plots, # TODO: consider if we could make this max_plots so that the data stream might also contain less than the specified amount of plots
            "xAxisLength": self.xAxisLength,
            "ylim": self.ylim
           }

    def init_draw(self, subfig):
        subfig.suptitle(self.name, fontsize=14)

        axes = subfig.subplots(self.n_plots, 1, sharex=True)
        if self.n_plots <= 1:
            axes = [axes]

        for name, ax in zip(self.names, axes):
            ax.set_ylim(*self.ylim)
            ax.set_xlim(0, self.xAxisLength)
            ax.set_yticks([])
            # ax.set_ylabel(name)
            # ax.tick_params(direction='in')
            # ax.tick_params(pad=-22)
            # print(ax.yaxis.label.get_position())
            # ax.yaxis.set_label_coords(0.1, 0.5)
            # print(ax.yaxis.label.get_position())

            # ax.yaxis.set_animated(True)
            # ax.yaxis.label.set_animated(True)

            ticks = np.linspace(0, self.xAxisLength, 11).astype(np.int)
            ax.set_xticks(ticks)
            ax.set_xticklabels(ticks - self.xAxisLength)
            # ax.xaxis.grid(False)

        axes[-1].set_xlabel("Time (ms)")
        xData = range(0, self.xAxisLength)  
        self.lines = [axes[i].plot(xData, self.yData[i], lw=2, animated=True)[0] for i in range(self.n_plots)]
        # self.labels = [ax.yaxis.label for ax in axes]
        self.labels = [ax.text(0.005, 0.95, name, fontproperties=ax.xaxis.label.get_font_properties(), rotation='horizontal', va='top', ha='left', transform = ax.transAxes) for name, ax in zip(self.names, axes)]
        # self.labels = [ax.text(self., self.ylim[1], name, rotation='horizontal', va='top', ha='left') for name, ax in zip(self.names, axes)]
        # self.labels = [ax.text(0.1, self.ylim[1] - 0.1, name, rotation='horizontal',va='top', ha='left', bbox=dict(boxstyle='square,pad=1', fc='none', ec='none')) for name, ax in zip(self.names, axes)]
        # self.axes = axes

        # handles = [ mpatches.Patch(color=None, label=key) for name in self.token_cols.items()]
        # legend = subfig.legend(handles=handles, loc='upper right')
        # legend.set_alpha(0) # TODO: for some reason the legend is transparent, no matter what i set here...
        # legend.set_zorder(100)

        def update (**kwargs):
            nonlocal self
            changes = []

            # update axis names
            if not self.name_queue.empty():
                while not self.name_queue.empty():
                    self.names = self.name_queue.get()

                for i, label in enumerate(self.labels):
                    label.set_text(self.names[i])
                    # label.set_label(self.names[i])
                    # changes.append(self.axes[i])
                    # changes.append(yaxis.label)

                # return changes

                # print(self.names, self.name_queue.empty())
                # print(str(self), 'Error in labels')
                # TODO: figure out if an early return messes up some of the data visualiztion, ie if some parts are thrown away. don't think so, but double check...

            # update axis values
            while not self.data_queue.empty():
                data = self.data_queue.get()
                for i in range(self.n_plots):
                    self.yData[i].append(data[i])
            
            for i in range(self.n_plots):
                # this is weird in behaviour as we need to overwrite this for some reason and cannot just use the view in the set_data part...
                self.yData[i] = self.yData[i][-self.xAxisLength:]
                self.lines[i].set_ydata(self.yData[i])
                changes.append(self.lines[i])

            # print(str(self), len(changes))
            # if len(changes) > 3:
            #     print(changes)

            # return self.lines 
            print(list(np.concatenate([self.lines, self.labels])))
            return list(np.concatenate([self.lines, self.labels]))

        return update

    def receive_channels(self, names, **kwargs):
        self.name_queue.put(names)

    def receive_data(self, data_frame, **kwargs):
        for vec in np.array(data_frame):
            self.data_queue.put(list(vec))  

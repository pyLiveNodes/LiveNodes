import collections
from queue import Queue
import numpy as np

from .blit import BlitManager
from .node import Node

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
    def __init__(self, idx, names, xAxisLength=5000, ylim=(-1.1, 1.1), name = "Draw Output Lines", dont_time = False):
        super().__init__(name=name, has_outputs=False, dont_time=dont_time)
        self.idx = idx
        self.names = names
        self.xAxisLength = xAxisLength
        self.ylim = ylim

        # render process
        self.yData = [[0] * self.xAxisLength] * len(self.names)
        # data generation process
        self.data_queue = [mp.SimpleQueue() for _ in range(len(self.names))]
    
    def _get_setup(self):
        return {\
            "name": self.name,
            "idx": self.idx,
            "names": self.names,
            "xAxisLength": self.xAxisLength,
            "ylim": self.ylim
           }

    def init_draw(self, subfig):
        n_plots = len(self.names)
        axes = subfig.subplots(n_plots, 1, sharex=True)
        if n_plots <= 1:
            axes = [axes]
        subfig.suptitle(self.name, fontsize=14)

        for i, ax in enumerate(axes):
            ax.set_ylim(*self.ylim)
            ax.set_xlim(0, self.xAxisLength)
            # ax.set_ylabel(np.array(self.recorded_channels)[self.channel_idx[i]], fontsize=10)
            ax.set_ylabel(self.names[i])
            ax.set_yticks([])
            ticks = np.linspace(0, self.xAxisLength, 11).astype(np.int)
            ax.set_xticks(ticks)
            ax.set_xticklabels(ticks - self.xAxisLength)
            # ax.xaxis.grid(False)

        axes[-1].set_xlabel("Time (ms)")
        xData = range(0, self.xAxisLength)  
        self.lines = [axes[i].plot(xData, self.yData[i], lw=2, animated=True)[0] for i in range(len(self.names))]
        self.axes = axes

        
        def update (**kwargs):
            nonlocal self

            for i in range(len(self.axes)):
                while not self.data_queue[i].empty():
                    self.yData[i].extend(list(self.data_queue[i].get()))

                # this is weird in behaviour as we need to overwrite this for some reason and cannot just use the view in the set_data part...
                self.yData[i] = self.yData[i][-self.xAxisLength:]
                self.lines[i].set_ydata(self.yData[i])
            return self.lines

        return update

    def receive_data(self, data_frame, **kwargs):
        periodData = np.array(data_frame).T

        for i in range(len(self.axes)):
            self.data_queue[i].put(periodData[self.idx[i]])
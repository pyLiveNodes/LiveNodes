import collections
import numpy as np

from .blit import BlitManager
from .node import Node

import time

class Draw_lines(Node):
    # TODO: consider removing the filter here and rather putting it into a filter node
    def __init__(self, idx, names, xAxisLength=5000, name = "Draw Output Lines", dont_time = False):
        super().__init__(name=name, has_outputs=False, dont_time=dont_time)
        self.idx = idx
        self.names = names
        self.xAxisLength = xAxisLength
    
    def _get_setup(self):
        return {\
            "name": self.name,
            "idx": self.idx,
            "names": self.names,
            "xAxisLength": self.xAxisLength
           }

    def init_draw(self, subfig):
        n_plots = len(self.names)
        axes = subfig.subplots(n_plots, 1, sharex=True)
        if n_plots <= 1:
            axes = [axes]
        subfig.suptitle("Raw Data", fontsize=14)

        for i, ax in enumerate(axes):
            ax.set_ylim(-1.1, 1.1)
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
        # self.yData = [collections.deque([0] * self.xAxisLength, maxlen=self.xAxisLength)] * len(self.names)
        self.yData = [[0] * self.xAxisLength] * len(self.names)
        # self.self.yData = np.zeros((len(names), self.xAxisLength)
        self.lines = [axes[i].plot(xData, list(self.yData[i]), lw=2, animated=True)[0] for i in range(len(self.names))]
        self.axes = axes
        # self.bm = BlitManager(subfig.canvas, self.lines)
        # self.time = time.time()
        # self.time_ctr = 1
        # return self.lines
        
        def update (**kwargs):
            for i in range(len(self.axes)):
                # print(np.array(list(self.yData[i])).shape)
                # if i ==0:
                #     print('----')
                    # print(list(self.yData[i]))
                    # print(list(self.yData_ref[i]))
                self.lines[i].set_ydata(list(self.yData[i]))
            return self.lines

        return update

    def add_data(self, data_frame, data_id=0):
        periodData = np.array(data_frame).T
        # print(periodData.shape)
        # print(periodData)
        # self.time_ctr += 1

        for i in range(len(self.axes)):
            # there is some weird bug in the deque, no clue why this doesn't work out correctly...
            # self.yData[i].extend(list(periodData[self.idx[i]]))
            self.yData[i].extend(periodData[self.idx[i]])
            self.yData[i] = self.yData[i][-self.xAxisLength:]
            # if i ==0:
            #     print('----')
            #     print(list(zip(list(self.yData_ref[i]), self.yData[i])))
            # self.lines[i].set_ydata(self.yData[i])
        # self.bm.update()
        # if self.time_ctr % 50 == 0:
            # print(f'{str(self)}: {self.time_ctr / (time.time() - self.time):.2f}fps, total frames: {self.time_ctr}')
        # return self.lines

import time
import numpy as np
from multiprocessing import Process
import threading
from .node import Node
import glob, random
import h5py
import pandas as pd

class Playback(Node):
    """
    Playsback previously recorded data.

    Expects the following setup variables:
    - files (str): glob pattern for files 
    - sample_rate (number): sample rate to simulate in frames per second
    # - batch_size (int, default=5): number of frames that are sent at the same time -> not implemented yet
    """
    has_inputs = False
    feeder_process = None
        
    def sender_process(self):
        """
        Streams the data and calls frame callbacks for each frame.
        """
        fs = glob.glob(self._setup.get('files'))
        sleep_time = 1 / self._setup.get('sample_rate')

        while(True):
            f = random.choice(fs)
            # print(f)
            # ref = pd.read_csv(f.replace('.h5', '.csv'), names=["act", "start", "end"])
            # targs = []
            # j = 0
            # for _, row in ref.iterrows():
            #     targs += [self.target_to_id["stand"]] * (row['start'] - j)
            #     targs += [self.target_to_id[row['act']]] * (row['end'] - row['start'] - j)
            #     j = row['end']

            with h5py.File(f, "r") as dataFile:
                dataSet = dataFile.get("data")
                start = 0
                end = len(dataSet)
                data = dataSet[:] # load into mem
                
                for i in range(start, end):
                    self.add_data(np.array([data[i]]))
                    time.sleep(sleep_time)

        # TODO: look at this implementation again, seems to be the more precise one
        # samples_per_frame = int(self.sample_rate / 1000 * self.frame_size_ms)
        # time_val = time.time()
        # time_val_init = time_val
        # for sample_cnt in range(0, len(self.data), samples_per_frame):
        #     samples = self.data[sample_cnt:sample_cnt+samples_per_frame]
        #     # if not self.asap:
        #     while time.time() - time_val < (1.0 / 1000.0) * self.frame_size_ms:
        #         time.sleep(0.000001)
        #     time_val = time_val_init + sample_cnt / self.sample_rate
        #     self.output_data(np.array(samples))
    
    def start_processing(self, recurse=True):
        """
        Starts the streaming process.
        """
        if self.feeder_process is None:
            self.feeder_process = threading.Thread(target=self.sender_process)
            self.feeder_process.start()
        super().start_processing(recurse)
        
    def stop_processing(self, recurse=True):
        """
        Stops the streaming process.
        """
        super().stop_processing(recurse)
        if self.feeder_process is not None:
            self.feeder_process.terminate()
        self.feeder_process = None

    def draw_raw(self, subfig, idx, names, xAxisLength=5000):
        n_plots = len(names)
        axes = subfig.subplots(n_plots, 1, sharex=True)
        if n_plots <= 1:
            axes = [axes]
        subfig.suptitle("Raw Data", fontsize=14)

        for i, ax in enumerate(axes):
            ax.set_ylim(-1.1, 1.1)
            ax.set_xlim(0, xAxisLength)
            # ax.set_ylabel(np.array(self.recorded_channels)[self.channel_idx[i]], fontsize=10)
            ax.set_ylabel(names[i])
            ax.set_yticks([])
            ticks = np.linspace(0, xAxisLength, 11).astype(np.int)
            ax.set_xticks(ticks)
            ax.set_xticklabels(ticks - xAxisLength)
            # ax.xaxis.grid(False)

        axes[-1].set_xlabel("Time (ms)")

        xData = range(0, xAxisLength)  
        yData = [[0] * xAxisLength] * len(names)
        # self.yData = np.zeros((len(names), xAxisLength)
        lines = [axes[i].plot(xData, yData[i], lw=2)[0] for i in range(len(names))]

        # should be returned by draw_raw and not called by itself
        # should return the lines it changed, in order for blit to work properly
        
        # this way all the draw details are hidden from everyone else
        # TODO: design! i would prefer to pass this to FuncAnimation directly, but the perdiodData needs to be saved until processed by all (!) independent draw calls
        def update(periodData, **kwargs):
            nonlocal yData, lines
            if len(periodData) > 0:
                periodData = np.array(periodData).T
                # print(periodData)
                # print(idx)
                # print(len(axes))
                # print('-----')

                for i in range(len(axes)):
                    yData[i].extend(periodData[idx[i]])
                    yData[i] = yData[i][-xAxisLength:]
                    lines[i].set_ydata(yData[i])
            return lines

        self._draw_updates.append(update)
        self.should_draw = True

        return update
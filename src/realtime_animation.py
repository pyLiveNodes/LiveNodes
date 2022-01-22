import numpy as np
import threading
import time
from matplotlib import animation
import matplotlib.pylab as plt
import math

class RealtimeAnimation:
    animationProcess = None
    pluxDevices = []
    pluxThread = None
    timer = 0
    n_frames_rendered = 0

    draw_setups = []
    _draw_uptades = [] # do not touch, automatically managed

    def closeAnimation(self, evt):
        self.pluxModule.stop()
        plt.close('all')
        self.onClose()

    def __init__(self, channel_names, pluxModule, font={'size': 6}, update_interval=30, xAxisLength=2000, animationDurationRecording=180 * 3600, onClose=lambda *args: None):
        self.font = font
        self.update_interval = update_interval
        self.xAxisLength = xAxisLength
        self.animationDurationRecording = animationDurationRecording
        self.onClose=onClose

        self.pluxModule = pluxModule
        self.recorded_channels = self.pluxModule.get_channel_names()
        self.channel_idx = np.isin(self.recorded_channels, channel_names).nonzero()[0]

        # re-order the channel_names array to correspond to the recorded order for easier indexing below
        self.channel_names = np.array(self.recorded_channels)[self.channel_idx]

        if len(self.channel_idx) <= 0 or np.count_nonzero(self.channel_idx) <= 0:
            print(self.recorded_channels, channel_names)
            raise Exception('Mismatching Channel Names')

        self.draw_setups.append(self.draw_raw)

    # interface as follows:
    # call this to setup axes, labels etc
    # this should return a function which takes data to update the graph
    def draw_raw(self, subfig, idx, names):
        n_plots = len(names)
        axes = subfig.subplots(n_plots, 1, sharex=True)
        if n_plots <= 1:
            axes = [axes]
        subfig.suptitle("Raw Data", fontsize=14)

        for i, ax in enumerate(axes):
            ax.set_ylim(-1.1, 1.1)
            ax.set_xlim(0, self.xAxisLength)
            # ax.set_ylabel(np.array(self.recorded_channels)[self.channel_idx[i]], fontsize=10)
            ax.set_ylabel(names[i])
            ax.set_yticks([])
            ticks = np.linspace(0, self.xAxisLength, 11).astype(np.int)
            ax.set_xticks(ticks)
            ax.set_xticklabels(ticks - self.xAxisLength)
            # ax.xaxis.grid(False)

        axes[-1].set_xlabel("Time (ms)")

        xData = range(0, self.xAxisLength)  
        yData = [[0] * self.xAxisLength] * len(names)
        # self.yData = np.zeros((len(names), self.xAxisLength)
        lines = [axes[i].plot(xData, yData[i], lw=2)[0] for i in range(len(names))]

        # should be returned by draw_raw and not called by itself
        # should return the lines it changed, in order for blit to work properly
        
        # this way all the draw details are hidden from everyone else
        def update(periodData, **kwargs):
            periodData = np.array(periodData).T

            for i in range(len(axes)):
                yData[i].extend(periodData[idx[i]])
                yData[i] = yData[i][-self.xAxisLength:]
                lines[i].set_ydata(yData[i])
            return lines

        return update

    def initial_draw_and_setup(self):
        # Full screen setup # not sure if still needed or where this should go
        # figManager = get_current_fig_manager()
        # figManager.full_screen_toggle()

        plt.rc('font', **self.font)

        self.fig = plt.figure(num=0, figsize =(16, 10))
        # self.fig.suptitle("ASK", fontsize='x-large')
        self.fig.canvas.manager.set_window_title("ASK")
        self.fig.canvas.mpl_connect("close_event", self.closeAnimation)

        if len(self.draw_setups) <= 0:
            raise Exception ('Must have at least one draw function registered')

        n_figs = len(self.draw_setups)
        cols = min(2, n_figs)
        rows = math.ceil(n_figs / cols) # ie max 3 columns
        
        # https://matplotlib.org/stable/gallery/subplots_axes_and_figures/subfigures.html

        subfigs = self.fig.subfigures(rows, cols) #, wspace=1, hspace=0.07)

        if len(self.draw_setups) == 1:
            subfigs = [subfigs] # matplotlibs subfigures call doesn't consistently return a list, but with n=1 the subfig directly...

        for setup_fn, subfig in zip(self.draw_setups, np.array(subfigs).flatten()):
            # draw_update_fn = setup_fn(subfig)
            draw_update_fn = setup_fn(subfig, idx=self.channel_idx, names=self.channel_names)
            self._draw_uptades.append(draw_update_fn)


    def draw (self, **kwargs):
        # call each draws' update function, which return the lines they changed, 
        # which in turn is returned by the update function back to matplotlib, 
        # which uses this information for blit (ie fast rendering)
        return list(np.concatenate([fn(**kwargs) for fn in self._draw_uptades], axis=0))

    def should_draw(self, data):
        return not self.pluxModule.endingFlag and time.time() - self.timer < self.animationDurationRecording and len(data) > 0

    def consume_buffer (self, buffer):
        return [buffer.get() for _ in range(buffer.qsize())]
        # return np.concatenate([self.pluxModule.buffer.get() for _ in range(self.pluxModule.buffer.qsize())])

    def update(self, i):
        periodData = self.consume_buffer(self.pluxModule.buffer)

        if self.should_draw(periodData):
            self.n_frames_rendered = i
            return self.draw(periodData)
        elif self.pluxModule.endingFlag:
            self.closeAnimation(None)
        return []

    def start(self):
        self.pluxThread = threading.Thread(target = self.pluxModule.start)
        self.pluxThread.daemon = True
        self.pluxThread.start()

        self.initial_draw_and_setup()
        self.timer = time.time()

        self.animationProcess = animation.FuncAnimation(fig=self.fig, func=self.update, interval=self.update_interval, blit=True)
        # plt.tight_layout()
        plt.show()

        # import matplotlib as mpl 
        # mpl.rcParams['animation.ffmpeg_path'] = '/usr/bin/ffmpeg'
        # self.animationProcess = animation.FuncAnimation(fig=self.fig, frames=200, save_count=200, func=self.update, interval=1, blit=True)
        # writervideo = animation.FFMpegWriter(fps=7) 
        # self.animationProcess.save("demo.mp4", writer=writervideo)
        
        el_time = time.time() - self.timer
        print(f"Rendered {self.n_frames_rendered} frames in {el_time:.2f} seconds. This equals {self.n_frames_rendered/el_time:.2f}fps.")

import numpy as np

from .node import View


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


class Draw_lines(View):
    channels_in = ['Data', 'Channel Names']
    channels_out = []

    category = "Draw"
    description = "" 

    example_init = {
        "name": "Draw Data Lines",
        "n_plots": 4,
        "xAxisLength": 5000,
        "sample_rate": 1000,
        "ylim": (-1.1, 1.1)
    }

    # TODO: move the sample rate into a data_stream?
    def __init__(self, n_plots=4, xAxisLength=5000, sample_rate=1000, ylim=(-1.1, 1.1), name = "Draw Output Lines", **kwargs):
        super().__init__(name=name, **kwargs)

        self.xAxisLength = xAxisLength
        self.sample_rate = sample_rate
        self.ylim = ylim
        self.n_plots = n_plots

        # computation process
        # yData follows the structure (time, channel)
        self.yData = np.zeros(xAxisLength * n_plots).reshape((xAxisLength, n_plots))

        # render process
        self.channel_names = list(map(str, range(n_plots)))

    def _settings(self):
        return {\
            "name": self.name,
            "n_plots": self.n_plots, # TODO: consider if we could make this max_plots so that the data stream might also contain less than the specified amount of plots
            "xAxisLength": self.xAxisLength,
            "sample_rate": self.sample_rate,
            "ylim": self.ylim
           }

    def _init_draw(self, subfig):
        subfig.suptitle(self.name, fontsize=14)

        axes = subfig.subplots(self.n_plots, 1, sharex=True)
        if self.n_plots <= 1:
            axes = [axes]

        for name, ax in zip(self.channel_names, axes):
            ax.set_ylim(*self.ylim)
            ax.set_xlim(0, self.xAxisLength)
            ax.set_yticks([])

            ticks = np.linspace(0, self.xAxisLength, 11).astype(np.int)
            ax.set_xticks(ticks)
            ax.set_xticklabels(- ticks / self.sample_rate)
            ax.invert_xaxis()
            # ax.xaxis.grid(False)

        axes[-1].set_xlabel("Time [sec]")
        xData = range(0, self.xAxisLength)  
        self.lines = [axes[i].plot(xData, np.zeros((self.xAxisLength)), lw=2, animated=True)[0] for i in range(self.n_plots)]

        # self.labels = []
        self.labels = [ax.text(0.005, 0.95, name, zorder=100, fontproperties=ax.xaxis.label.get_font_properties(), rotation='horizontal', va='top', ha='left', transform = ax.transAxes) for name, ax in zip(self.channel_names, axes)]
        # self.labels = [ax.text(0, 0.5, name, fontproperties=ax.xaxis.label.get_font_properties(), rotation='vertical', va='center', ha='right', transform = ax.transAxes) for name, ax in zip(self.channel_names, axes)]

        def update (data, channel_names):
            nonlocal self
            # Not sure why the changes part doesn't work, (not even with zorder)
            # -> could make stuff more efficient, but well...
            # changes = []

            if self.channel_names != channel_names:
                self.channel_names = channel_names

                for i, label in enumerate(self.labels):
                    label.set_text(self.channel_names[i])

            for i in range(self.n_plots):
                self.lines[i].set_ydata(data[i])

            return list(np.concatenate([self.lines, self.labels]))

        return update


    def _should_process(self, data=None, channel_names=None):
        return data is not None and \
            (self.channel_names is not None or channel_names is not None)

    # data should follow the (batch/file, time, channel) format
    def process(self, data, channel_names=None):
        if channel_names is not None:
            self.channel_names = channel_names

        # if (batch/file, time, channel)
        d = np.vstack(np.array(data)[:, :, :self.n_plots])

        # if (batch/file, time, channel)
        # d = np.vstack(np.array(data)[:, :self.n_plots])

        # self.info(np.array(data).shape, d.shape, self.yData.shape)

        self.yData = np.roll(self.yData, d.shape[0], axis=0)
        self.yData[:d.shape[0]] = d

        # TODO: consider if we really always want to send the channel names? -> seems an unecessary overhead (but cleaner code atm, maybe massage later...)
        self._emit_draw(data=list(self.yData.T), channel_names=self.channel_names)

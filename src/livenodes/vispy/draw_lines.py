import numpy as np

from livenodes.core.viewer import View_Vispy
import vispy.plot as vp

from . import local_registry

@local_registry.register
class Draw_lines(View_Vispy):
    """
    Draw all received data channels as line plot over time.

    Furthest right is the current time, left is x second in the past.

    Draws on a matplotlib canvas.
    """

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

    def __init__(self,
                 n_plots=4,
                 xAxisLength=5000,
                 sample_rate=1000,
                 ylim=(-1.1, 1.1),
                 name="Draw Output Lines",
                 **kwargs):
        super().__init__(name=name, **kwargs)

        self.xAxisLength = xAxisLength
        self.sample_rate = sample_rate
        self.ylim = ylim
        self.n_plots = n_plots

        # computation process
        # yData follows the structure (time, channel)
        self.yData = np.zeros(xAxisLength * n_plots).reshape(
            (xAxisLength, n_plots))
        self.xData = (-np.arange(xAxisLength)/sample_rate)[::-1]

        # render process
        self.channel_names = [str(i) for i in range(n_plots)]

    def _settings(self):
        return {\
            "name": self.name,
            "n_plots": self.n_plots, # TODO: consider if we could make this max_plots so that the data stream might also contain less than the specified amount of plots
            "xAxisLength": self.xAxisLength,
            "sample_rate": self.sample_rate,
            "ylim": self.ylim
           }

    def _init_draw(self, fig):
        # TODO: consider creating the vp.fig in the View_Vispy class and pass it here (similar to the matplotlib design)

        # for name, ax in zip(self.channel_names, axes):
        #     ax.set_ylim(*self.ylim)
        #     ax.set_xlim(0, self.xAxisLength)
        #     ax.set_yticks([])

        #     ticks = np.linspace(0, self.xAxisLength, 11).astype(np.int)
        #     ax.set_xticks(ticks)
        #     ax.set_xticklabels(-ticks / self.sample_rate)
        #     ax.invert_xaxis()
        #     # ax.xaxis.grid(False)

        # axes[-1].set_xlabel("Time [sec]")

        # https://vispy.org/api/vispy.plot.plotwidget.html?highlight=plotwidget#vispy.plot.plotwidget.PlotWidget.plot
        self.lines = [
            fig[i, 0].plot(data=(self.xData, self.yData[:, i]), marker_size=0, width=2.0) for i, channel in enumerate(self.channel_names)
        ]

        for line, pwidget in zip(self.lines, fig.plot_widgets):
            # x_data = line._line.pos[:, 0]
            # y_data = line._line.pos[:, 1]
            x_range = (-self.xAxisLength / self.sample_rate, 0)
            y_range = (-1.1, 1.1)
            # x_range = x_data.min(), x_data.max()
            # y_range = y_data.min(), y_data.max()

            pwidget.view.camera.set_range(x=x_range, y=y_range)

        # self.labels = []
        # self.labels = [
        #     ax.text(0.005,
        #             0.95,
        #             name,
        #             zorder=100,
        #             fontproperties=ax.xaxis.label.get_font_properties(),
        #             rotation='horizontal',
        #             va='top',
        #             ha='left',
        #             transform=ax.transAxes)
        #     for name, ax in zip(self.channel_names, axes)
        # ]

        # self.labels = [ax.text(0, 0.5, name, fontproperties=ax.xaxis.label.get_font_properties(), rotation='vertical', va='center', ha='right', transform = ax.transAxes) for name, ax in zip(self.channel_names, axes)]

        def update(data, channel_names):
            nonlocal self

            # if self.channel_names != channel_names:
            #     self.channel_names = channel_names

            #     for i, label in enumerate(self.labels):
            #         label.set_text(self.channel_names[i])

            for i in range(self.n_plots):
                self.lines[i].set_data((self.xData, data[i]))
            
            # x_range = 0, 1000
            # y_range = np.min(data), y_data.max()
            # return x_range, y_range

        return update

    def _should_process(self, data=None, channel_names=None):
        return data is not None and \
            (self.channel_names is not None or channel_names is not None)

    # data should follow the (batch/file, time, channel) format
    def process(self, data, channel_names=None, **kwargs):
        if channel_names is not None:
            self.channel_names = channel_names

        # if (batch/file, time, channel)
        d = np.vstack(np.array(data)[:, :, :self.n_plots])

        self.yData = np.roll(self.yData, -d.shape[0], axis=0)
        self.yData[-d.shape[0]:] = d

        # TODO: consider if we really always want to send the channel names? -> seems an unecessary overhead (but cleaner code atm, maybe massage later...)
        # self.debug('emitting draw', self.yData.shape)
        self._emit_draw(data=list(self.yData.T),
                        channel_names=self.channel_names)

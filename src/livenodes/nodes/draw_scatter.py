import numpy as np

from livenodes.core.viewer import View

from . import local_registry


@local_registry.register
class Draw_scatter(View):
    """
    Draw all the first two received data channels as scatter plot.
    
    Time is represented via alpha values. The most current point is opaque the furthest point away is at 10% alpha.

    Draws on a matplotlib canvas.
    """

    channels_in = ['Data', 'Channel Names']
    channels_out = []

    category = "Draw"
    description = ""

    example_init = {
        "name": "Draw Data Scatter",
        "n_scatter_points": 50,
        "ylim": (-1.1, 1.1)
    }

    # TODO: move the sample rate into a data_stream?
    def __init__(self,
                 n_scatter_points=50,
                 ylim=(-1.1, 1.1),
                 name="Draw Output Scatter",
                 **kwargs):
        super().__init__(name=name, **kwargs)

        self.n_scatter_points = n_scatter_points
        self.ylim = ylim

        # computation process
        # yData follows the structure (time, channel)
        self.data = np.zeros(n_scatter_points * 2).reshape(
            (n_scatter_points, 2))

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

        self.ax = subfig.subplots(1, 1)
        self.ax.set_xlim(-0.5, 0.5)
        self.ax.set_ylim(-0.5, 0.5)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)

        # self.ax.set_xlabel(self.plot_names[0])
        # self.ax.set_ylabel(self.plot_names[1])

        alphas = np.linspace(0.1, 1, self.n_scatter_points)
        xData = self.data[:, 0]
        yData = self.data[:, 1]

        scatter = self.ax.scatter(xData, yData, alpha=alphas)

        # self.labels = [self.ax.text(0.005, 0.95, name, zorder=100, fontproperties=self.ax.xaxis.label.get_font_properties(), rotation='horizontal', va='top', ha='left', transform = ax.transAxes) for name, ax in zip(self.channel_names, axes)]

        def update(data, channel_names):
            nonlocal self
            # Not sure why the changes part doesn't work, (not even with zorder)
            # -> could make stuff more efficient, but well...
            # changes = []

            scatter.set_offsets(data)

            return [scatter]

        return update

    def _should_process(self, data=None, channel_names=None):
        return (data is not None) and \
            (self.channel_names is not None or channel_names is not None)

    # data should follow the (batch/file, time, channel) format
    def process(self, data, channel_names=None, **kwargs):
        if channel_names is not None:
            self.channel_names = channel_names

        # if (batch/file, time, channel)
        d = np.vstack(np.array(data)[:, :, :2])

        # if (batch/file, time, channel)
        # d = np.vstack(np.array(data)[:, :2])

        self.data = np.roll(self.data, d.shape[0], axis=0)
        self.data[:d.shape[0]] = d

        # TODO: consider if we really always want to send the channel names? -> seems an unecessary overhead (but cleaner code atm, maybe massage later...)
        self._emit_draw(data=self.data[:self.n_scatter_points],
                        channel_names=self.channel_names)

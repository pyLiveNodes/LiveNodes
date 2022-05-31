import numpy as np

from livenodes.core.viewer import View

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

from . import local_registry



@local_registry.register
class Draw_hbars(View):
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
        "xlim": (-0.05, 1.05)
    }

    # TODO: move the sample rate into a data_stream?
    def __init__(self,
                 n_plots=4,
                 xlim=(-0.05, 1.05),
                 name="Draw Output Lines",
                 **kwargs):
        super().__init__(name=name, **kwargs)

        self.xlim = xlim
        self.n_plots = n_plots

        # computation process
        self.xData = np.zeros(n_plots)

        # render process
        self.channel_names = ["" for _ in range(n_plots)]

    def _settings(self):
        return {\
            "name": self.name,
            "n_plots": self.n_plots, # TODO: consider if we could make this max_plots so that the data stream might also contain less than the specified amount of plots
            "xlim": self.xlim
           }

    def _init_draw(self, subfig):
        subfig.suptitle(self.name, fontsize=14)

        axes = subfig.subplots(self.n_plots, 1, sharex=True)
        if self.n_plots <= 1:
            axes = [axes]

        for name, ax in zip(self.channel_names, axes):
            ax.set_ylim(0, 1)
            ax.set_yticks([])
            ax.yaxis.grid(False)

            ax.set_xlim(*self.xlim)
            # ticks = np.linspace(*self.xlim, 10).astype(np.int)
            # ax.set_xticks(ticks)
            # ax.xaxis.grid(False)

        # axes[-1].set_xlabel("Time [sec]")
        # TODO: consider changign this not to be an axis per bar, but just one axis with multiple bars...
        # print(axes[0].barh(0.5, self.xData[0], animated=True))
        # print(axes[0].barh(0.5, self.xData[0], animated=True).patches)
        self.hbars = [
            axes[i].barh(0.5, self.xData[i], animated=True).patches[0] for i in range(self.n_plots)
        ]

        # self.labels = []
        self.labels = [
            ax.text(0.005,
                    0.95,
                    name,
                    zorder=100,
                    fontproperties=ax.xaxis.label.get_font_properties(),
                    rotation='horizontal',
                    va='top',
                    ha='left',
                    transform=ax.transAxes)
            for name, ax in zip(self.channel_names, axes)
        ]

        def update(data, channel_names):
            nonlocal self
           
            if self.channel_names != channel_names:
                self.channel_names = channel_names

                for i, label in enumerate(self.labels):
                    label.set_text(self.channel_names[i])

            for i in range(self.n_plots):
                self.hbars[i].set_width(data[i])

            return list(np.concatenate([self.hbars, self.labels]))

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

        # TODO: consider if we really always want to send the channel names? -> seems an unecessary overhead (but cleaner code atm, maybe massage later...)
        # self.debug('emitting draw', self.yData.shape)
        self._emit_draw(data=d[-1], channel_names=self.channel_names)

import numpy as np

from livenodes.core.node import Node

from . import local_registry

@local_registry.register
class Annotate_channel(Node):
    channels_in = ['Data', 'Channel Names']
    channels_out = ['Data', 'Channel Names', 'Annotation']

    category = "Annotation"
    description = ""

    example_init = {
        'name': 'Channel Annotation',
        'channel_name': 'Pushbutton',
        'targets': ['Pressed', 'Released']
    }

    def __init__(self,
                 channel_name,
                 targets,
                 name="Channel Annotation",
                 **kwargs):
        super().__init__(name=name, **kwargs)

        self.channel_name = channel_name
        self.targets = targets
        self.name = name

        self.idx = None

    def _settings(self):
        return {\
            "name": self.name,
            "channel_name": self.channel_name,
            "targets": self.targets,
           }

    def _should_process(self, data=None, channel_names=None):
        return data is not None and \
            (self.idx is not None or channel_names is not None)

    def process(self, data, channel_names=None, **kwargs):
        if channel_names is not None:
            self.idx = np.array(channel_names) == self.channel_name
            self._emit_data(np.array(channel_names)[~self.idx],
                            channel="Channel Names")

        d = np.array(data)
        self._emit_data(d[:, :, ~self.idx])
        self._emit_data(np.where(d[:, :, self.idx] >= 0, self.targets[1],
                                 self.targets[0]),
                        channel="Annotation")

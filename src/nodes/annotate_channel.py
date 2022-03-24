import numpy as np
import multiprocessing as mp

from .node import Node

class Annotate_channel(Node):
    def __init__(self, channel_name, targets, name = "Channel Annotation", **kwargs):
        super().__init__(name=name, **kwargs)
        self.channel_name = channel_name
        self.targets = targets
        self.name = name

        self.idx = None

    @staticmethod
    def info():
        return {
            "class": "Annotate_channel",
            "file": "Annotate_channel.py",
            "in": ["Data", "Channel Names"],
            "out": ["Data", "Channel Names", "Annotation"],
            "init": {
                "name": "Channel Annotation",
                "channel_name": "Pushbutton",
                "targets": ["Pressed", "Released"],
            },
            "category": "Annotation"
        }
        
    @property
    def in_map(self):
        return {
            "Data": self.receive_data,
            "Channel Names": self.receive_channels
        }

    def _settings(self):
        return {\
            "name": self.name,
            "channel_name": self.channel_name,
            "targets": self.targets,
           }

    def receive_channels(self, channel_names, **kwargs):
        self.idx = np.array(channel_names) == self.channel_name
        self._emit_data(np.array(channel_names)[~self.idx], channel="Channel Names")

    def process(self, data, **kwargs):
        if self.idx is not None:
            d = np.array(data_frame)
            self._emit_data(d[:,~self.idx])
            self._emit_data(np.where(d[:,self.idx] >= 0, self.targets[1], self.targets[0]), channel="Annotation")
        
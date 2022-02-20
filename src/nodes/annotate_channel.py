import numpy as np
import multiprocessing as mp

from .node import Node

class Annotate_channel(Node):
    def __init__(self, channel_name, targets, name = "Channel Annotation", dont_time = False):
        super().__init__(name=name, dont_time=dont_time)
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

    def _get_setup(self):
        return {\
            "name": self.name,
            "channel_name": self.channel_name,
            "targets": self.targets,
           }

    def receive_channels(self, channel_names, **kwargs):
        self.idx = np.array(channel_names) == self.channel_name
        self.send_data(np.array(channel_names)[~self.idx], data_stream="Channel Names")

    def receive_data(self, data_frame, **kwargs):
        if self.idx is not None:
            d = np.array(data_frame)
            self.send_data(d[:,~self.idx])
            self.send_data(np.where(d[:,self.idx] >= 0, self.targets[1], self.targets[0]), data_stream="Annotation")
        
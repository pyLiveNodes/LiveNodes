import numpy as np
from .node import Node

# TODO: rather use the same mechanism as in the mkr library so that all features can be added at once
class Feature_avg(Node):
    def receive_data(self, data_frame, **kwargs):
        # print(np.array(data_frame).shape, np.mean(data_frame, axis=0).shape)
        self.send_data([np.mean(data_frame, axis=0)])

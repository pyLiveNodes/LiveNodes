import numpy as np
from .node import Node

# TODO: rather use the same mechanism as in the mkr library so that all features can be added at once
class Feature_avg(Node):
    def add_data(self, data_frame, data_id=0):
        # print(np.array(data_frame).shape, np.mean(data_frame, axis=0).shape)
        self.output_data([np.mean(data_frame, axis=0)])

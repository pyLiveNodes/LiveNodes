import numpy as np
from .node import Node

import BioKIT

class Biokit_to_fs(Node):
    # def add_data(self, data_frame, data_id=0):
    #     fs = BioKIT.FeatureSequence()
    #     fs.setMatrix(np.array(data_frame))
    #     self.output_data(fs)
    def add_data(self, data_frame, data_id=0):
        mcfs = []
        for channel in np.array(data_frame).T:
            fs = BioKIT.FeatureSequence()
            fs.setMatrix(np.atleast_2d(channel).T)
            mcfs.append(fs)
        self.output_data(mcfs)

import numpy as np
from .node import Node

import BioKIT

class Biokit_from_fs(Node):
    # def add_data(self, fs, data_id=0):
    #     self.output_data(fs.getMatrix())

    def add_data(self, mcfs, data_id=0):
        dim1 = mcfs[0].getLength(
        )  # assume same length of all FeatureSequences
        dim2 = 0
        for fs in mcfs:
            dim2 += fs.getDimensionality()
        ar = np.empty((dim1, dim2))
        counter = 0
        for fs in mcfs:
            fsar = fs.getMatrix()
            ar[:, counter:(counter+fsar.shape[1])] = fsar
            counter += fsar.shape[1]
        self.output_data(ar)
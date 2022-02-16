import numpy as np
from .node import Node

from .biokit import BioKIT

class Biokit_from_fs(Node):
    def receive_data(self, fs, **kwargs):
        self.send_data(fs.getMatrix())

    @staticmethod
    def info():
        return {
            "class": "Biokit_from_fs",
            "file": "biokit_from_fs.py",
            "in": ["Data"],
            "out": ["Data"],
            "init": {
                "name": "str"
            },
            "category": "BioKIT"
        }

    # def receive_data(self, mcfs, data_id=0):
    #     dim1 = mcfs[0].getLength(
    #     )  # assume same length of all FeatureSequences
    #     dim2 = 0
    #     for fs in mcfs:
    #         dim2 += fs.getDimensionality()
    #     ar = np.empty((dim1, dim2))
    #     counter = 0
    #     for fs in mcfs:
    #         fsar = fs.getMatrix()
    #         ar[:, counter:(counter+fsar.shape[1])] = fsar
    #         counter += fsar.shape[1]
    #     self.send_data(ar)
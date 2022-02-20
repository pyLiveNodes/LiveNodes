import numpy as np
from .node import Node

from .biokit import BioKIT

class Biokit_to_fs(Node):
    def receive_data(self, data_frame, **kwargs):
        fs = BioKIT.FeatureSequence()
        fs.setMatrix(np.array(data_frame))
        self.send_data(fs)
        
    @staticmethod
    def info():
        return {
            "class": "Biokit_to_fs",
            "file": "biokit_to_fs.py",
            "in": ["Data"],
            "out": ["Data"],
            "init": {
                "name": "Name"
            },
            "category": "BioKIT"
        }

    # def receive_data(self, data_frame, data_id=0):
    #     mcfs = []
    #     for channel in np.array(data_frame).T:
    #         fs = BioKIT.FeatureSequence()
    #         fs.setMatrix(np.atleast_2d(channel).T)
    #         mcfs.append(fs)
    #     self.send_data(mcfs)

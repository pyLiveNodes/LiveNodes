import numpy as np
from .node import Node

from .biokit import BioKIT

class Biokit_to_fs(Node):
    def process(self, data, **kwargs):
        fs = BioKIT.FeatureSequence()
        fs.setMatrix(np.array(data_frame))
        self._emit_data(fs)
        
    @staticmethod
    def info():
        return {
            "class": "Biokit_to_fs",
            "file": "biokit_to_fs.py",
            "in": ["Data"],
            "out": ["Data"],
            "init": {
                "name": "To Feature Sequence"
            },
            "category": "BioKIT"
        }

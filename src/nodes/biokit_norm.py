import numpy as np
from .node import Node

import BioKIT

class Biokit_norm(Node):
    def __init__(self, name="Node", has_inputs=True, has_outputs=True, dont_time=False):
        super().__init__(name, has_inputs, has_outputs, dont_time)

        self.meanSubtraction = BioKIT.ZNormalization()
        self.meanSubtraction.resetMeans()


    def receive_data(self, fs, **kwargs):
        self.meanSubtraction.updateMeans([fs], 1.0, True)
        normed = self.meanSubtraction.subtractMeans([fs], 1.0)[0] # TODO: check if the [0] here is correct...
        self.send_data(normed)

    @staticmethod
    def info():
        return {
            "class": "Biokit_norm",
            "file": "biokit_norm.py",
            "in": ["Data"],
            "out": ["Data"],
            "init": {
                "name": "str"
            },
            "category": "BioKIT"
        }
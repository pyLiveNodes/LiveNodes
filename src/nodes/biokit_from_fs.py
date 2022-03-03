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
                "name": "From Feature Sequence"
            },
            "category": "BioKIT"
        }

import numpy as np
from .node import Node

from .biokit import BioKIT


class Biokit_to_fs(Node):
    """
    Transforms a Stream (batch/file, time, channel) into (batch/file, BioKIT Feature Sequence).
    """

    category = "BioKIT"
    description = ""

    example_init = {'name': 'To BioKIT'}

    def process_time_series(self, ts):
        fs = BioKIT.FeatureSequence()
        fs.setMatrix(np.array(ts))
        return fs

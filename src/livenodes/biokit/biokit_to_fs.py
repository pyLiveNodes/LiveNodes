import numpy as np

from livenodes.core.node import Node
from livenodes.biokit.biokit import BioKIT

from . import local_registry


@local_registry.register
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

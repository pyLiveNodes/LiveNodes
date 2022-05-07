from livenodes.core.node import Node

from . import local_registry

@local_registry.register
class Biokit_from_fs(Node):
    """
    Transforms a Stream of (batch/file, BioKIT Feature Sequence) into (batch/file, time, channel).

    Requires a BioKIT Feature Sequence Stream
    """

    category = "BioKIT"
    description = ""

    example_init = {'name': 'From BioKIT'}

    def process_time_series(self, ts):
        return ts.getMatrix()

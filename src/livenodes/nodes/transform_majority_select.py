import numpy as np

from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Transform_majority_select(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Transform"
    description = ""

    example_init = {'name': 'Majority Select'}

    # in: (time, channel) (becaue process_time_serise and not process)
    def process_time_series(self, ts):
        # as is (time, channel) -> we want the uniques over time in one channel (not the uniques across channles on each time step)
        val, counts = np.unique(ts, axis=0, return_counts=True)
        return [
            val[np.argmax(counts, axis=0)]
        ]  # TODO: not sure if this is fully correct, maybe write some tests, but works for now

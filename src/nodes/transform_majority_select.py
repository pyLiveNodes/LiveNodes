import numpy as np
from .node import Node


class Transform_majority_select(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Transform"
    description = ""

    example_init = {'name': 'Name'}

    def process_time_series(self, ts):
        val, counts = np.unique(ts, axis=-1, return_counts=True)
        return [
            val[np.argmax(counts, axis=-1)]
        ]  # TODO: not sure if this is fully correct, maybe write some tests, but works for now

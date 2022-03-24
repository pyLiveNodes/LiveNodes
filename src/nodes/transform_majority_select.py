import numpy as np
from .node import Node

class Transform_majority_select(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Transform"
    description = "" 

    example_init = {'name': 'Name'}
    
    def process(self, data):
        val, counts = np.unique(data, axis=-1, return_counts=True)
        self._emit_data([val[np.argmax(counts, axis=-1)]]) # TODO: not sure if this is fully correct, maybe write some tests, but works for now
        
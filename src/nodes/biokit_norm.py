import numpy as np
from .node import Node

from .biokit import BioKIT

class Biokit_norm(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "BioKIT"
    description = "" 

    example_init = {'name': 'Norm'}

    def __init__(self, name="Norm", **kwargs):
        super().__init__(name, **kwargs)

        self.meanSubtraction = BioKIT.ZNormalization()
        self.meanSubtraction.resetMeans()


    def process(self, data):
        self.meanSubtraction.updateMeans([data], 1.0, True)
        normed = self.meanSubtraction.subtractMeans([data], 1.0)[0] # TODO: check if the [0] here is correct...
        self._emit_data(normed)
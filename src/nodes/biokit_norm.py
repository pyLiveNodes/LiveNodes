import numpy as np
from .node import Node

from .biokit import BioKIT

class Biokit_norm(Node):
    category = "BioKIT"
    description = "" 

    example_init = {'name': 'Norm'}

    def __init__(self, name="Norm", **kwargs):
        super().__init__(name, **kwargs)

        self.meanSubtraction = BioKIT.ZNormalization()
        self.meanSubtraction.resetMeans()


    def process_time_series(self, ts):
        self.meanSubtraction.updateMeans([ts], 1.0, True)
        normed = self.meanSubtraction.subtractMeans([ts], 1.0)
        return normed[0]
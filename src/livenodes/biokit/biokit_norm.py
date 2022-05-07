from livenodes.core.node import Node
from livenodes.biokit.biokit import BioKIT

from . import local_registry


@local_registry.register
class Biokit_norm(Node):
    """
    Z-Normalisierung on BioKIT Feature Sequences. 
    For each Batch: Subtracts the current running mean and norm the variance to one. 
    
    The running mean is updated with each new batch of data.
    The current implementation never resets the means.

    Requires a BioKIT Feature Sequence Stream
    """

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

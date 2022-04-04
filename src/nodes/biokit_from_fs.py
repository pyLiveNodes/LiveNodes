import numpy as np
from .node import Node

from .biokit import BioKIT

class Biokit_from_fs(Node):
    category = "BioKIT"
    description = "" 

    example_init = {'name': 'Name'}

    def process_time_series(self, ts):
        return ts.getMatrix()


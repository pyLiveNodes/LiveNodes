import numpy as np
from .node import Node

from .biokit import BioKIT

class Biokit_from_fs(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "BioKIT"
    description = "" 

    example_init = {'name': 'Name'}

    def process(self, data)
        self._emit_data(fs.getMatrix())


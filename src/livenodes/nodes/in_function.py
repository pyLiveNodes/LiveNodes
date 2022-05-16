import numpy as np
import time

from livenodes.core.sender import Sender

from . import local_registry


@local_registry.register
class In_function(Sender):
    """
   
    """

    channels_in = []
    channels_out = [
        'Data', 'Meta', 'Channel Names'
    ]

    category = "Data Source"
    description = ""

    example_init = {
        "function": "sin",
        "meta": {
            "sample_rate": 100,
            "targets": ["target 1"],
            "channels": ["Channel 1"]
        },
        "emit_at_once": 1,
        "name": "Data input",
    }

    # TODO: consider using a file for meta data instead of dictionary...
    def __init__(self,
                 meta,
                 function="sin",
                 emit_at_once=1,
                 name="Function Input",
                 **kwargs):
        super().__init__(name, **kwargs)

        self.meta = meta
        self.function = function
        self.emit_at_once = emit_at_once

        self.sample_rate = meta.get('sample_rate')
        self.targets = meta.get('targets')
        self.channels = meta.get('channels')

    def _settings(self):
        return {\
            "emit_at_once": self.emit_at_once,
            "function": self.function,
            "meta": self.meta
        }

    def _run(self):
        """
        Streams the data and calls frame callbacks for each frame.
        """
        self._emit_data(self.meta, channel="Meta")
        self._emit_data(self.channels, channel="Channel Names")

        ctr = 0
        n_channels = len(self.channels)
        
        def linear(x): return x/1000
        try:
            fn = getattr(np, self.function)
        except:
            fn = linear

        while True:
            samples = np.linspace(ctr, ctr + self.emit_at_once, 1)
            res = fn(samples)
            res = np.array([np.array([res] * n_channels).T])
            self._emit_data(res)
            ctr += self.emit_at_once
            time.sleep(1./self.sample_rate)
            yield True

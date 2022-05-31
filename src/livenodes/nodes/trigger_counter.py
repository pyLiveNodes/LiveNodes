import numpy as np

from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Trigger_counter(Node):
    """
   
    """

    channels_in = ['Data']
    channels_out = ['Trigger', 'Meta', 'Time to Event']

    # TODO: create variante that has an optional input stream that it uses to sync itself with
    # maybe just introduce a counter trigger, ie every x samples send a trigger?

    category = "Data Source"
    description = ""

    example_init = {
        "resting": 0,
        "signal": 1,
        "duration": 1,
        "every_x_samples": 100,
        "sample_rate": 100,
        "name": "Data input",
    }

    def __init__(self,
                 resting = 0,
                 signal = 1,
                 duration = 1,
                 every_x_samples = 100,
                 sample_rate = 100, # TODO: move this into an input or something
                 name="Function Input",
                 **kwargs):
        super().__init__(name, **kwargs)

        self.every_x_samples = every_x_samples
        self.sample_rate = sample_rate
        self.duration = duration
        self.ctr = every_x_samples

        self.resting = resting
        self.signal = signal

        self.meta = {'sample_rate': sample_rate, 'duration': duration, 'every_x_samples': every_x_samples, 'resting': resting, 'signal': signal}

    def _settings(self):
        return {\
            "resting": self.resting,
            "signal": self.signal,
            "resting": self.resting,
            "signal": self.signal,
            "sample_rate": self.sample_rate,
            "every_x_samples": self.every_x_samples,
            "duration": self.duration,
        }

    def _should_process(self, data=None, **kwargs):
        return data is not None

    def process(self, data, **kwargs):
        d = np.array(data, dtype=object)
        r = d.size
        if len(d.shape) > 0:
            r = d.shape[0]

        self.ctr -= r

        if self.ctr <= self.duration:
            self._emit_data(self.signal, channel="Trigger")
        else:
            self._emit_data(self.resting, channel="Trigger")
        
        if self.ctr <= 0:
            self.ctr = self.every_x_samples

        self._emit_data(self.ctr / self.sample_rate, channel="Time to Event")
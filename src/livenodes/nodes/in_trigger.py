import time

from livenodes.core.sender import Sender

from . import local_registry


@local_registry.register
class In_trigger(Sender):
    """
   
    """

    channels_in = []
    channels_out = [
        'Trigger', 'Meta', 'Time to Event'
    ]

    category = "Data Source"
    description = ""

    example_init = {
        "resting": 0,
        "signal": 1,
        "duration": 1,
        "interval": 100,
        "sample_rate": 100,
        "name": "Data input",
    }

    def __init__(self,
                 sample_rate = 100,
                 resting = 0,
                 signal = 1,
                 duration = 1,
                 interval = 100,
                 name="Function Input",
                 **kwargs):
        super().__init__(name, **kwargs)

        self.sample_rate = sample_rate
        self.interval = interval
        self.duration = duration

        self.resting = resting
        self.signal = signal

        self.meta = {'sample_rate': sample_rate, 'duration': duration, 'interval': interval, 'resting': resting, 'signal': signal}

    def _settings(self):
        return {\
            "resting": self.resting,
            "signal": self.signal,
            "resting": self.resting,
            "signal": self.signal,
            "interval": self.interval,
            "duration": self.duration
        }

    def _run(self):
        """
        Streams the data and calls frame callbacks for each frame.
        """
        self._emit_data(self.meta, channel="Meta")

        ctr = self.interval
        
        while True:
            if ctr <= self.duration:
                self._emit_data(self.signal, channel="Trigger")
            else:
                self._emit_data(self.resting, channel="Trigger")
            
            ctr -= 1

            if ctr <= 0:
                ctr = self.interval

            self._emit_data(ctr / self.sample_rate, channel="Time to Event")

            # TODO: update this to be more precise 
            time.sleep(1./self.sample_rate)
            yield True
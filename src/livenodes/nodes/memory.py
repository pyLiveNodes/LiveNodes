import numpy as np

from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Memory(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Basic"
    description = ""

    example_init = {'name': 'Name'}

    def __init__(self,
                 length=None,
                 concat_batches=True,
                 name="Memory",
                 **kwargs):
        super().__init__(name=name, **kwargs)

        self.length = length
        self.buffer = np.array([])
        self.concat_batches = concat_batches

    def _settings(self):
        return {\
            "length": self.length,
            "concat_batches": self.concat_batches
           }

    def process(self, data, **kwargs):
        d = np.array(data)

        if self.concat_batches:
            d = np.vstack(d)

            if self.buffer.size == 0:
                self.buffer = d
            else:
                # TODO: in case of self.length != none, a np.roll is probably a more efficient
                self.buffer = np.vstack([self.buffer, d])

            if self.length != None:
                # self.buffer = self.buffer[-int(self.length / self.buffer.shape[1]):]
                self.buffer = self.buffer[-self.length:]

            self._emit_data([self.buffer])
        else:
            # self.buffer.extend(data)
            raise NotImplementedError(
                'No offline file based routine implemented yet for windowing.')
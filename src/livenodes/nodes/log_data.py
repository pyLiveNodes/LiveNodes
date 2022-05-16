from livenodes.core.node import Node

from . import local_registry


@local_registry.register
class Log_data(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Basic"
    description = ""

    example_init = {'name': 'Name'}

    def process(self, data, **kwargs):
        self.info(data)
        self._emit_data(data)

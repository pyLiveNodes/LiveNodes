from .node import Node

class Log_data(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Basic"
    description = "" 

    example_init = {'name': 'Name'}

    def process(self, data):
        self._log(data)
        self._emit_data(data)
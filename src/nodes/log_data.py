from .node import Node

class Log_data(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Basic"
    description = "" 

    example_init = {'name': 'Name'}

    def process(self, data, **kwargs):
        self._log(data_frame)
        self._emit_data(data_frame)
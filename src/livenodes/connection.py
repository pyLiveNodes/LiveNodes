class Connection():
    # TODO: consider creating a channel registry instead of using strings?
    def __init__(self,
                 emitting_node,
                 receiving_node,
                 emitting_channel="Data",
                 receiving_channel="Data",
                 connection_counter=0):
        self._emitting_node = emitting_node
        self._receiving_node = receiving_node
        self._emitting_channel = emitting_channel
        self._receiving_channel = receiving_channel
        self._connection_counter = connection_counter

    def __repr__(self):
        return f"{str(self._emitting_node)}.{self._emitting_channel} -> {str(self._receiving_node)}.{self._receiving_channel}"

    def to_dict(self):
        return {
            "emitting_node": str(self._emitting_node),
            "receiving_node": str(self._receiving_node),
            "emitting_channel": self._emitting_channel,
            "receiving_channel": self._receiving_channel,
            "connection_counter": self._connection_counter
        }

    def _set_connection_counter(self, counter):
        self._connection_counter = counter

    def _similar(self, other):
        return self._emitting_node == other._emitting_node and \
            self._receiving_node == other._receiving_node and \
            self._emitting_channel == other._emitting_channel and \
            self._receiving_channel == other._receiving_channel

    def __eq__(self, other):
        return self._similar(
            other) and self._connection_counter == other._connection_counter

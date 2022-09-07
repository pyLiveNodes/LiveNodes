class Connection():
    # TODO: consider creating a channel registry instead of using strings?
    def __init__(self,
                 emit_node: 'Connectionist',
                 recv_node: 'Connectionist',
                 emit_port: 'Port',
                 recv_port: 'Port',
                 connection_counter=0):
        self._emit_node = emit_node
        self._recv_node = recv_node
        self._emit_port = emit_port
        self._recv_port = recv_port
        self._connection_counter = connection_counter

    def __repr__(self):
        return f"{str(self._emit_node)}.{str(self._emit_port)} -> {str(self._recv_node)}.{str(self._recv_port)}"

    def to_dict(self):
        return {
            "emit_node": str(hash(self._emit_node)),
            "recv_node": str(hash(self._recv_node)),
            "emit_port": self._emit_port.key,
            "recv_port": self._recv_port.key,
            "connection_counter": self._connection_counter
        }

    def _set_connection_counter(self, counter):
        self._connection_counter = counter

    def _similar(self, other):
        return self._emit_node == other._emit_node \
            and self._recv_node == other._recv_node \
            and self._emit_port == other._emit_port \
            and self._recv_port == other._recv_port

    def __eq__(self, other):
        return self._similar(other) \
            and self._connection_counter == other._connection_counter

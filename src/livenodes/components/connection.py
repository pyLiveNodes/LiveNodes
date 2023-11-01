class Connection():
    # TODO: consider creating a channel registry instead of using strings?
    def __init__(self,
                 emit_node: 'Connectionist',
                 recv_node: 'Connectionist',
                 emit_port: 'Port',
                 recv_port: 'Port'):
        self._emit_node = emit_node
        self._recv_node = recv_node
        self._emit_port = emit_port
        self._recv_port = recv_port

    def __repr__(self):
        return f"{str(self._emit_node)}.{str(self._emit_port)} -> {str(self._recv_node)}.{str(self._recv_port)}"

    def serialize_compact(self) -> str:
        return f"{str(self._emit_node)}.{str(self._emit_port.key)} -> {str(self._recv_node)}.{str(self._recv_port.key)}"

    @staticmethod
    def deserialize_compact(compact_str):
        emit, recv = compact_str.split(" -> ")
        emit_node, emit_port = emit.split(".")
        recv_node, recv_port = recv.split(".")
        return {
            "emit_node": str(emit_node),
            "recv_node": str(recv_node),
            "emit_port": emit_port,
            "recv_port": recv_port
        }

    def to_dict(self):
        return {
            "emit_node": str(self._emit_node),
            "recv_node": str(self._recv_node),
            "emit_port": self._emit_port.key,
            "recv_port": self._recv_port.key
        }

    def __eq__(self, other):
        return self._emit_node == other._emit_node \
            and self._recv_node == other._recv_node \
            and self._emit_port == other._emit_port \
            and self._recv_port == other._recv_port
from livenodes.components.node_logger import Logger

class Bridge(Logger):

    # _build thread
    # TODO: this is a serious design flaw:
    # if __init__ is called in the _build / main thread, the queues etc are not only shared between the nodes using them, but also the _build thread
    # explicitly: if a local queue is created for two nodes inside of the same process computer (ie mp process) it is still shared between two processes (main and computer/worker)
    # however: we might be lucky as the main thread never uses it / keeps it.
    def __init__(self, _from=None, _to=None, _data_type=None):
        super().__init__()
        self._from = _from
        self._to = _to
        self._data_type = _data_type

        # _to thread
        self._read = {}

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}>:{id(self)}"

    # called by mp_storage on it's initalization and calls to ready everything to be able to send and receive data
    # _computer thread
    def ready_send(self):
        raise NotImplementedError()

    # called by mp_storage on it's initalization and calls to ready everything to be able to send and receive data
    # _computer thread
    def ready_recv(self):
        raise NotImplementedError()


    @staticmethod
    def can_handle(_from, _to, _data_type=None):
        # Returns
        #   - True if it can handle this connection
        #   - 0-10 how high the handle cost (indicates which implementation to use if multiple can handle this)
        raise NotImplementedError()

    # _from thread
    def close(self):
        raise NotImplementedError()

    # _from thread
    def put(self):
        raise NotImplementedError()

    # _to thread (called by _should_process)
    def closed_and_empty():
        raise NotImplementedError()

    # _to thread
    async def onclose(self):
        raise NotImplementedError()

    # _to thread
    async def update(self):
        raise NotImplementedError()

    # _to thread
    def discard_before(self, ctr):
        self._read = {
            key: val
            for key, val in self._read.items() if key >= ctr
        }

    # _to thread
    def get(self, ctr):
        # in the process and thread case the queue should always be empty if we arrive here
        # This should also never be executed in process or thread, as then the update function does not block and keys are skipped!
        if ctr in self._read:
            return True, self._read[ctr]
        return False, None

import asyncio
import queue
import threading as th
from livenodes.components.computer import parse_location

from .bridge_abstract import Bridge

class Bridge_thread(Bridge):

    # _build thread
    # TODO: this is a serious design flaw:
    # if __init__ is called in the _build / main thread, the queues etc are not only shared between the nodes using them, but also the _build thread
    # explicitly: if a local queue is created for two nodes inside of the same process computer (ie mp process) it is still shared between two processes (main and computer/worker)
    # however: we might be lucky as the main thread never uses it / keeps it.
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # both threads
        self.queue = queue.Queue()
        self.closed_event = th.Event()

    # _computer thread
    def ready_send(self):
        # self.queue = queue.Queue()
        # self.closed_event = th.Event()
        pass

    # _computer thread
    def ready_recv(self):
        pass

    # _build thread
    @staticmethod
    def can_handle(_from, _to, _data_type=None):
        # can handle same process, and same thread, with cost 1 (shared mem would be faster, but otherwise this is quite good)
        from_host, from_process, from_thread = parse_location(_from)
        to_host, to_process, to_thread = parse_location(_to)
        return from_host == to_host and from_process == to_process, 4

    # _from thread
    def close(self):
        self.closed_event.set()

    # _from thread
    def put(self, ctr, item):
        self.queue.put_nowait((ctr, item))

    # _to thread
    async def onclose(self):
        while True:
            await asyncio.sleep(0.01)
            if self.closed_and_empty():
                self.debug('Closed Event set and queue empty -- telling multiprocessing data storage')
                break

    # _to thread
    def closed(self):
        return self.closed_event.is_set()

    # _to thread
    def empty(self):
        return self.queue.empty() and self._read == {}

    def closed_and_empty(self):
        return self.closed() and self.empty()

    # _to thread
    async def update(self):
        # # print('waiting for asyncio to receive a value')
        got_item = False
        while not got_item:
            try:
                itm_ctr, item = self.queue.get_nowait()
                got_item = True
            except queue.Empty:
                await asyncio.sleep(0.001)
        self._read[itm_ctr] = item
        return itm_ctr



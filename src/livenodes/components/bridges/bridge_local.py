import asyncio
import threading as th

from livenodes import REGISTRY

from .bridge_abstract import Bridge

@REGISTRY.bridges.decorator
class Bridge_local(Bridge):
    
    # _build thread
    # TODO: this is a serious design flaw: 
    # if __init__ is called in the _build / main thread, the queues etc are not only shared between the nodes using them, but also the _build thread
    # explicitly: if a local queue is created for two nodes inside of the same process computer (ie mp process) it is still shared between two processes (main and computer/worker)
    # however: we might be lucky as the main thread never uses it / keeps it.
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # both threads (?)
        self.queue = None
        self.closed_event = None
        
    # _computer thread
    def ready_send(self):
        self.queue = asyncio.Queue()
        self.closed_event = th.Event()

    # _computer thread
    def ready_recv(self):
        pass

    # _build thread
    @staticmethod
    def can_handle(_from, _to, _data_type=None):
        # can handle same process, and same thread, with cost 1 (shared mem would be faster, but otherwise this is quite good)
        return _from == _to, 1
        # return True, 1
        
    # _from thread
    def close(self):
        self.closed_event.set()

    # _from thread
    def put(self, ctr, item):
        # print('putting value', ctr)
        self.queue.put_nowait((ctr, item))

    # _to thread
    def closed(self):
        return self.closed_event.is_set()

    # _to thread
    async def onclose(self):
        while True:
            await asyncio.sleep(0.01)
            if self.closed() and self.empty():
                self.debug('Closed Event set and queue empty -- telling multiprocessing data storage')
                return

    # _to thread
    def empty(self):
        return self.queue.qsize() <= 0
        
    # _to thread
    async def update(self):
        # print('waiting for asyncio to receive a value')
        try:
            itm_ctr, item = await self.queue.get()
            self._read[itm_ctr] = item
            return itm_ctr
        except Exception as err:
            self.logger.exception(f'Could not get value')
            self.error(err)

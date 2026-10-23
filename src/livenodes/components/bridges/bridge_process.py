import asyncio
import multiprocessing as mp
import queue

from livenodes.components.computer import parse_location

from .bridge_thread import Bridge_thread

# Sent through the queue by close(). The queue is FIFO, so once the receiver has read the marker it has
# read every item put before it. mp.Queue.empty() can't tell that: it is True while an item is still
# being pickled by the feeder thread or sits in the pipe.
_END_OF_STREAM = "__livenodes_bridge_end_of_stream__"


class Bridge_process(Bridge_thread):

    # _build thread
    # TODO: this is a serious design flaw:
    # if __init__ is called in the _build / main thread, the queues etc are not only shared between the nodes using them, but also the _build thread
    # explicitly: if a local queue is created for two nodes inside of the same process computer (ie mp process) it is still shared between two processes (main and computer/worker)
    # however: we might be lucky as the main thread never uses it / keeps it.
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.queue = mp.Queue()
        self.closed_event = mp.Event()
        # _to thread: set once the end-of-stream marker was read
        self._end_of_stream = False

    # _from thread
    def close(self):
        # Never blocks: waiting for the feeder to flush here can deadlock two processes that send to each
        # other (both event loops stuck in close while neither drains its input pipe).
        if not self.closed_event.is_set():
            self.queue.put_nowait((None, _END_OF_STREAM))
        self.closed_event.set()

    @staticmethod
    def can_handle(_from, _to, _data_type=None):
        # can handle same process, and same thread, with cost 1 (shared mem would be faster, but otherwise this is quite good)
        from_host, from_process, from_thread = parse_location(_from)
        to_host, to_process, to_thread = parse_location(_to)
        return from_host == to_host, 5

    # _to thread
    def closed(self):
        return self._end_of_stream

    # _to thread
    def empty(self):
        # every item before the marker has been received once closed() is True; only unprocessed ones remain
        return self._read == {}

    # _to thread
    async def update(self):
        while True:
            try:
                itm_ctr, item = self.queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.001)
                continue
            if itm_ctr is None and isinstance(item, str) and item == _END_OF_STREAM:
                self._end_of_stream = True
                # None tells the node that an input closed: items waiting for this input may be
                # processable now (it no longer counts as required). Nothing follows on this bridge.
                return None
            self._read[itm_ctr] = item
            return itm_ctr

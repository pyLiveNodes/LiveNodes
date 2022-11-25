import multiprocessing as mp

from livenodes.components.computer import parse_location

from livenodes import REGISTRY

from .bridge_thread import Bridge_thread

@REGISTRY.bridges.decorator
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
        

    @staticmethod
    def can_handle(_from, _to, _data_type=None):
        # can handle same process, and same thread, with cost 1 (shared mem would be faster, but otherwise this is quite good)
        from_host, from_process, from_thread = parse_location(_from)
        to_host, to_process, to_thread = parse_location(_to)
        return from_host == to_host, 5

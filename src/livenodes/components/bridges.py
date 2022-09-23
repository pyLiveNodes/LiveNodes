import asyncio
import threading
import aioprocessing
from .node_logger import Logger

from .connection import Connection
from .computer import parse_location

from livenodes import REGISTRY, get_registry

class Bridge(Logger):
    
    def __init__(self, _from=None, _to=None, _data_type=None):
        super().__init__()
        self._from = _from
        self._to = _to
        self._data_type = _data_type

        # _to thread
        self._read = {}


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


@REGISTRY.bridges.decorator
class Bridge_local(Bridge):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # both threads (?)
        self.queue = asyncio.Queue()
        self.closed_event = threading.Event()
        
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
                return

    # _to thread
    def empty(self):
        return self.queue.qsize() <= 0
        
    # _to thread
    async def update(self):
        # print('waiting for asyncio to receive a value')
        itm_ctr, item = await self.queue.get()
        self._read[itm_ctr] = item
        return itm_ctr


@REGISTRY.bridges.decorator
class Bridge_threads(Bridge):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # both threads
        self.queue = aioprocessing.AioQueue()
        self.closed_event = aioprocessing.AioEvent()
        
    # _build thread
    @staticmethod
    def can_handle(_from, _to, _data_type=None):
        # can handle same process, and same thread, with cost 1 (shared mem would be faster, but otherwise this is quite good)
        from_host, from_process, from_thread = parse_location(_from)
        to_host, to_process, to_thread = parse_location(_to)
        return from_host == to_host and from_process == to_process, 2

    # _from thread
    def close(self):
        self.closed_event.set()

    # _from thread
    def put(self, ctr, item):
        # print('putting value', ctr)
        self.queue.put_nowait((ctr, item))

    # _to thread
    async def onclose(self):
        await self.closed_event.coro_wait()
        await self.queue.coro_join()
        
    # _to thread
    async def update(self):
        # print('waiting for asyncio to receive a value')
        itm_ctr, item = await self.queue.get()
        self._read[itm_ctr] = item
        return itm_ctr

@REGISTRY.bridges.decorator
class Bridge_processes(Bridge_threads):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def can_handle(_from, _to, _data_type=None):
        # can handle same process, and same thread, with cost 1 (shared mem would be faster, but otherwise this is quite good)
        from_host, from_process, from_thread = parse_location(_from)
        to_host, to_process, to_thread = parse_location(_to)
        return from_host == to_host, 3

        

class Multiprocessing_Data_Storage():
    def __init__(self) -> None:
        self.bridges = {}
        self.input_connections = []

        # will be filled by the nodes we input to, so that we know where to put this...
        # TODO: not sure if this is the best paradigm still...
        self.bridges_out = {}

    @staticmethod
    def resolve_bridge(connection: Connection):
        emit_loc = connection._emit_node.compute_on
        recv_loc = connection._recv_node.compute_on

        print('----')
        print('Bridging', emit_loc, recv_loc)
        print('Bridging', parse_location(emit_loc), parse_location(recv_loc))

        possible_bridges_pair = []
        for bridge in get_registry().bridges.values():
            can_handle, cost = bridge.can_handle(_from=emit_loc, _to=recv_loc)
            if can_handle:
                possible_bridges_pair.append((cost, bridge))

        if len(possible_bridges_pair) == 0:
            raise ValueError('No known bridge for connection', connection)

        possible_bridges = list(zip(*list(sorted(possible_bridges_pair, key=lambda t:t[0]))))[1]
        print('Using Bridge: ', possible_bridges[0])
        return possible_bridges[0](_from=emit_loc, _to=recv_loc)

    # _to thread
    def all_closed(self):
        return all([b.closed() for b in self.bridges])

    # _to thread
    async def on_all_closed(self):
        await asyncio.gather(*[b.onclose() for b in self.bridges.values()])
        print('All bridges empty and closed')

    # _to thread
    def set_inputs(self, input_connections):
        self.input_connections = input_connections
        for con in input_connections:
            self.bridges[con._recv_port.key] = self.resolve_bridge(con)
            # con._emit_node.data_storage.

    # def receive_output_object(self, output_connection, bridge):
    #     self.bridges_out[output_connection._emit_port.key] = bridge

    # TODO: may be removed?
    def empty(self):
        return all([q.empty() for q in self.bridges.values()])


    # _to thread
    def get(self, ctr):
        res = {}
        # update current state, based on own clock
        for key, queue in self.bridges.items():
            # discard everything, that was before our own current clock
            found_value, cur_value = queue.get(ctr)

            if found_value:
                # TODO: instead of this key transformation/tolower consider actually using classes for data types... (allows for gui names alongside dev names and not converting between the two)
                res[key] = cur_value
        return res 
    
    # _to thread
    def discard_before(self, ctr):
        for bridge in self.bridges.values():
            bridge.discard_before(ctr) 

    # _from thread
    def put(self, connection, ctr, data):
        # print('data storage putting value', connection._recv_port.key, type(self.bridges[connection._recv_port.key]))
        self.bridges[connection._recv_port.key].put(ctr, data)

    # _from thread
    def close_bridges(self, node):
        for con in self.input_connections:
            if con._emit_node == node:
                self.bridges[con._recv_port.key].close()

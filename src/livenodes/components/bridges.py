import asyncio
import threading
import aioprocessing
from .node_logger import Logger

from .connection import Connection
from .computer import parse_location

from livenodes import REGISTRY, get_registry

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

    # # _build thread
    # def get_endpoints(self):
    #     # return write_endpoint, read_endpoint
    #     raise NotImplementedError()

    # # _computer thread
    # def set_endpoints(self, write_endpoint, read_endpoint):
    #     # return write_endpoint, read_endpoint
    #     raise NotImplementedError()

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
        self.closed_event = threading.Event()

    # _computer thread
    def ready_recv(self):
        pass

    # _build thread
    @staticmethod
    def can_handle(_from, _to, _data_type=None):
        # can handle same process, and same thread, with cost 1 (shared mem would be faster, but otherwise this is quite good)
        return _from == _to, 1
        # return True, 1

    # # _build thread
    # def get_endpoints(self):
    #     # return write_endpoint, read_endpoint
    #     return self.queue, self.queue

    # # _computer thread
    # def set_endpoints(self, write_endpoint, read_endpoint):
        

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
    
    # _build thread
    # TODO: this is a serious design flaw: 
    # if __init__ is called in the _build / main thread, the queues etc are not only shared between the nodes using them, but also the _build thread
    # explicitly: if a local queue is created for two nodes inside of the same process computer (ie mp process) it is still shared between two processes (main and computer/worker)
    # however: we might be lucky as the main thread never uses it / keeps it.
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # both threads
        self.queue = aioprocessing.AioQueue()
        self.closed_event = aioprocessing.AioEvent()
        
    # _computer thread
    def ready_send(self):
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
        itm_ctr, item = await self.queue.coro_get()
        self._read[itm_ctr] = item
        return itm_ctr

@REGISTRY.bridges.decorator
class Bridge_processes(Bridge_threads):

    # _build thread
    # TODO: this is a serious design flaw: 
    # if __init__ is called in the _build / main thread, the queues etc are not only shared between the nodes using them, but also the _build thread
    # explicitly: if a local queue is created for two nodes inside of the same process computer (ie mp process) it is still shared between two processes (main and computer/worker)
    # however: we might be lucky as the main thread never uses it / keeps it.
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def can_handle(_from, _to, _data_type=None):
        # can handle same process, and same thread, with cost 1 (shared mem would be faster, but otherwise this is quite good)
        from_host, from_process, from_thread = parse_location(_from)
        to_host, to_process, to_thread = parse_location(_to)
        return from_host == to_host, 3

        

# def resolve_bridge(conneciton):
#     pass

# class Stream_Receiver():
    
#     def __init__(self, input_endpoints) -> None:
#         pass

# class Stream_Sender():

#     def __init__(self, output_endpoints) -> None:
#         pass


# TODO: this should be part of Node class or at least a mixin!
class Multiprocessing_Data_Storage():
    # enpoints should be dicts with con.key: bridge
    def __init__(self, input_endpoints, output_endpoints) -> None:
        # self.bridges = {}
        # self.input_connections = []

        self.in_bridges = input_endpoints
        self.out_bridges = output_endpoints

        for b in self.out_bridges.values():
            b.ready_recv()

        for b in self.in_bridges.values():
            b.ready_send()
        
    @staticmethod
    def resolve_bridge(connection: Connection):
        emit_loc = connection._emit_node.compute_on
        recv_loc = connection._recv_node.compute_on

        print('----')
        print(connection)
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
        
        bridge = possible_bridges[0](_from=emit_loc, _to=recv_loc)
        endpoint_send, endpoint_receive = bridge, bridge
        return endpoint_send, endpoint_receive

    # _to thread
    def all_closed(self):
        return all([b.closed() for b in self.in_bridges])

    # _to thread
    async def on_all_closed(self):
        await asyncio.gather(*[b.onclose() for b in self.in_bridges.values()])
        print('All bridges empty and closed')

    # # _to thread
    # def set_inputs(self, input_connections):
    #     self.input_connections = input_connections
    #     for con in input_connections:
    #         self.bridges[con._recv_port.key] = self.resolve_bridge(con)
            # con._emit_node.data_storage.

    # # _build thread
    # def get_endpoints(self):
    #     # return tuple<node_id, 
    #     pass

    # # _worker thread
    # def set_endpoints(self, bridges):
    #     pass

    # def receive_output_object(self, output_connection, bridge):
    #     self.bridges_out[output_connection._emit_port.key] = bridge

    # TODO: may be removed?
    def empty(self):
        return all([q.empty() for q in self.in_bridges.values()])


    # _to thread
    def get(self, ctr):
        res = {}
        # update current state, based on own clock
        for key, queue in self.in_bridges.items():
            # discard everything, that was before our own current clock
            found_value, cur_value = queue.get(ctr)

            if found_value:
                # TODO: instead of this key transformation/tolower consider actually using classes for data types... (allows for gui names alongside dev names and not converting between the two)
                res[key] = cur_value
        return res 
    
    # _to thread
    def discard_before(self, ctr):
        for bridge in self.in_bridges.values():
            bridge.discard_before(ctr) 

    # _from thread
    def put(self, connection, ctr, data):
        # print('data storage putting value', connection._recv_port.key, type(self.bridges[connection._recv_port.key]))
        self.out_bridges[connection._recv_port.key].put(ctr, data)

    # _from thread
    def close_bridges(self, node):
        # for con in self.input_connections:
        #     if con._emit_node == node:
        #         self.out_bridges[con._recv_port.key].close()
        for bridge in self.out_bridges.values():
            bridge.close()

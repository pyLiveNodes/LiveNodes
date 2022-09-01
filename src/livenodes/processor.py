from enum import IntEnum
from sqlite3 import connect
import numpy as np
import multiprocessing as mp
import threading
import queue

from livenodes.connection import Connection

from .node_logger import Logger

class Location(IntEnum):
    SAME = 1
    THREAD = 2
    PROCESS = 3
    # SOCKET = 4



class Bridge_local():

    def __init__(self):
        self.queue = queue.Queue()
        self._read = {}

    def put(self, ctr, item):
        self.queue.put((ctr, item))

    def update(self, timeout=0.01):
        try:
            itm_ctr, item = self.queue.get(block=True, timeout=timeout)
            self._read[itm_ctr] = item
            return True, itm_ctr
        except queue.Empty:
            pass
        return False, -1

    def empty_queue(self):
        while not self.queue.empty():
            itm_ctr, item = self.queue.get()
            # TODO: if itm_ctr already exists, should we not rather extend than overwrite it? (thinking of the mulitple emit_data per process call examples (ie window))
            # TODO: yes! this is what we should do :D
            self._read[itm_ctr] = item

    def discard_before(self, ctr):
        self._read = {
            key: val
            for key, val in self._read.items() if key >= ctr
        }

    def get(self, ctr):
        self.empty_queue()

        if ctr in self._read:
            return True, self._read[ctr]
        return False, None


class Bridge_mp(Bridge_local):
    def __init__(self):
        super().__init__()
        self.queue = mp.Queue()

    def get(self, ctr):
        # in the process and thread case the queue should always be empty if we arrive here
        # This should also never be executed in process or thread, as then the update function does not block and keys are skipped!
        if ctr in self._read:
            return True, self._read[ctr]
        return False, None


class Multiprocessing_Data_Storage():
    def __init__(self) -> None:
        self.bridges = {}

    @staticmethod
    def resolve_bridge(connection: Connection):
        emit_loc = connection._emit_node.compute_on
        recv_loc = connection._recv_node.compute_on

        if emit_loc in [Location.PROCESS] or recv_loc in [Location.PROCESS]:
            return Bridge_mp()
        else:
            return Bridge_local()

    def set_inputs(self, input_connections):
        for con in input_connections:
            self.bridges[con._recv_port.key] = self.resolve_bridge(con)

    # can be called from any process
    def put(self, connection, ctr, data):
        self.bridges[connection._recv_port.key].put(ctr, data)

    # will only be called within the processesing process
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
    
    # will only be called within the processesing process
    def discard_before(self, ctr):
        for bridge in self.bridges.values():
            bridge.discard_before(ctr) 


class Processor(Logger):

    def __init__(self, compute_on=Location.SAME, **kwargs) -> None:
        super().__init__(**kwargs)
        self.compute_on = compute_on

        self._subprocess_info = {}
        if self.compute_on in [Location.PROCESS]:
            self._subprocess_info = {
                "process": None,
                "termination_lock": mp.Lock()
            }
        elif self.compute_on in [Location.THREAD]:
            self._subprocess_info = {
                "process": None,
                "termination_lock":
                threading.Lock()  # as this is called from the main process
            }

        self.info('Computing on: ', self.compute_on)    

        self.data_storage = Multiprocessing_Data_Storage()
        # this will be instantiated once the whole thing starts, as before connections (and compute_ons) might change

    # required if we do the same=main process thing, as we cannot create the processes on instantiation
    def spawn_processes(self):
        graph_nodes = self.discover_graph(self)
        for node in graph_nodes:
            if 'process' in node._subprocess_info and node._subprocess_info['process'] is None:
                if node.compute_on == Location.PROCESS:
                    node._subprocess_info['process'] = mp.Process(
                        target=node._process_on_proc)
                elif node.compute_on == Location.THREAD:
                    node._subprocess_info['process'] = threading.Thread(
                        target=node._process_on_proc)


    def _acquire_lock(self, lock, block=True, timeout=None):
        if self.compute_on in [Location.PROCESS]:
            res = lock.acquire(block=block, timeout=timeout)
        elif self.compute_on in [Location.THREAD]:
            if block:
                res = lock.acquire(blocking=True,
                                   timeout=-1 if timeout is None else timeout)
            else:
                res = lock.acquire(
                    blocking=False)  # forbidden to specify timeout
        else:
            raise Exception(
                'Cannot acquire lock in non multi process/threading environment'
            )
        return res

    def start_node(self):
        # create bridges and storage based on the connections we have once we've started?
        # as then compute_on and number of connections etc should not change anymore
        self.data_storage.set_inputs(self.input_connections)

        # TODO: consider moving this in the node constructor, so that we do not have this nested behaviour processeses due to parents calling their childs start()
        # TODO: but maybe this is wanted, just buggy af atm
        if self.compute_on in [Location.PROCESS, Location.THREAD]:
            # if self.compute_on == Location.PROCESS:
            #     self._subprocess_info['process'] = mp.Process(
            #         target=self._process_on_proc)
            # elif self.compute_on == Location.THREAD:
            #     self._subprocess_info['process'] = threading.Thread(
            #         target=self._process_on_proc)

            self.info('create subprocess')
            self._acquire_lock(self._subprocess_info['termination_lock'])
            self.info('start subprocess')
            self._subprocess_info['process'].start()
        elif self.compute_on in [Location.SAME]:
            self._call_user_fn(self._onstart, '_onstart')
            self.info('Executed _onstart')

    def stop_node(self):
        if self.compute_on in [Location.PROCESS, Location.THREAD]:
            self.info(self._subprocess_info['process'].is_alive(),
                        self._subprocess_info['process'].name)
            self._subprocess_info['termination_lock'].release()
            self._subprocess_info['process'].join(1)
            self.info(self._subprocess_info['process'].is_alive(),
                        self._subprocess_info['process'].name)

            if self.compute_on in [Location.PROCESS]:
                self._subprocess_info['process'].terminate()
                self.info(self._subprocess_info['process'].is_alive(),
                            self._subprocess_info['process'].name)
        elif self.compute_on in [Location.SAME]:
            self.info('Executing _onstop')
            self._call_user_fn(self._onstop, '_onstop')


    def trigger_process(self, ctr):
        if self.compute_on in [Location.SAME]:
            # same and threads both may be called directly and do not require a notification
            self._process(ctr)
        elif self.compute_on in [Location.PROCESS, Location.THREAD]:
            # Process and thread both activley wait on the _received_data queues and therefore do not require an active trigger to process
            pass
        else:
            raise Exception(f'Location {self.compute_on} not implemented yet.')

    def _process_on_proc(self):
        self.info('Started subprocess')

        self._call_user_fn(self._onstart, '_onstart')
        self.info('Executed _onstart')

        # as long as we do not receive a termination signal, we will wait for data to be processed
        # the .empty() is not reliable (according to the python doc), but the best we have at the moment
        was_queue_empty_last_iteration = 0
        queue_empty = False
        was_terminated = False

        # one iteration takes roughly 0.00001 * channels -> 0.00001 * 10 * 100 = 0.01
        while not was_terminated or was_queue_empty_last_iteration < 10:
            could_acquire_term_lock = self._acquire_lock(
                self._subprocess_info['termination_lock'], block=False)
            was_terminated = was_terminated or could_acquire_term_lock
            # block until signaled that we have new data
            # as we might receive not data after having received a termination
            #      -> we'll just poll, so that on termination we do terminate after no longer than 0.1seconds
            # self.info(was_terminated, was_queue_empty_last_iteration)
            queue_empty = True
            for queue in self.data_storage.bridges.values():
                found_value, ctr = queue.update(timeout=0.00001)
                if found_value:
                    self._process(ctr)
                    queue_empty = False
            if queue_empty:
                was_queue_empty_last_iteration += 1
            else:
                was_queue_empty_last_iteration = 0

        self.info('Executing _onstop')
        self._call_user_fn(self._onstop, '_onstop')

        self.info('Finished subprocess')

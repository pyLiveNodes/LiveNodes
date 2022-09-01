from enum import IntEnum
import numpy as np
import multiprocessing as mp
import threading

from .node_logger import Logger

class Location(IntEnum):
    SAME = 1
    THREAD = 2
    PROCESS = 3
    # SOCKET = 4


class Bridge ():

    def __init__(self, emit, recv) -> None:
        self.emit = emit
        self.recv = recv

    def send(self, clock, payload):
        self.recv.receive_data(clock, payload=payload)


def resolve_bridge(emit_node, receive_node):
    return Bridge(emit_node, receive_node)
    

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

    # def receive_data(self, ctr, payload):
    #     """
    #     called in location of emitting node
    #     """
    #     # store all received data in their according mp.simplequeues
    #     for key, val in payload.items():
    #         self.error(f'Received: "{key}" with clock {ctr}')
    #         self._received_data[key].put(ctr, val)

    #     # FIX ME! TODO: this is a pain in the butt
    #     # Basically:
    #     # 1. node A runs in a thread
    #     # 2. node B runs on another thread
    #     # 3. A calls emit_data in its own process()
    #     # 4. this triggers a call of B.receive_data, but in the context of As thread
    #     # which means, that suddently B is not running in another thread, but this one.
    #     # this clashes if b also waits for an input from yet another thread
    #     # mainly this also means, that the QueueHelper hack reads from it's queues at different threads and therefore cannot combine the information
    #     # not sure how to fix this though :/ for now: we'll just not execute anything in Location.SAME and fix this later
    #     self.trigger_process(ctr)

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
            for queue in self._received_data.values():
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

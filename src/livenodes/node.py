from enum import IntEnum
from functools import partial
import numpy as np
import time
import multiprocessing as mp
import queue
import threading
import traceback

from .clock_register import Clock_Register
from .perf import Time_Per_Call, Time_Between_Call
from .port import Port

from .node_connector import Connectionist
from .node_logger import Logger
from .node_serializer import Serializer


class Location(IntEnum):
    SAME = 1
    THREAD = 2
    PROCESS = 3
    # SOCKET = 4


class QueueHelperHack():

    def __init__(self, compute_on=Location.SAME):
        # self.queue = mp.Queue()
        # The assumption behind this compute_on check is not correct -> (as long as the processes are created inside the node.node_start() method)
        # if we are on thread or queue -> always use mp as we are in a suprocess to the *first* parent, that called start_node on us
        # if we are on same, but any of our parents is in a different thread/process -> still use mp
        # if we are on same and all our parents are in the same thread/process -> only now we can use the normal queue
        #   -> but again: only if they are in the same thread/process, not if they have the same compute_on value!

        # TODO: figure out how to incorporate this tho, as queue.Queue() is probably more efficient
        if compute_on in [Location.PROCESS, Location.THREAD]:
            self.queue = mp.Queue()
        elif compute_on in [Location.SAME]:
            self.queue = queue.Queue()

        self.compute_on = compute_on

        self._read = {}

    def put(self, ctr, item):
        self.queue.put((ctr, item))
        # self.queue.put_nowait((ctr, item))

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
        if self.compute_on == Location.SAME:
            # This is only needed in the location.same case, as in the process and thread case the queue should always be empty if we arrive here
            # This should also never be executed in process or thread, as then the update function does not block and keys are skipped!
            self.empty_queue()

        if ctr in self._read:
            return True, self._read[ctr]
        return False, None



class Node(Connectionist, Logger, Serializer):
    # === Information Stuff =================
    # ports_in = [Port('port 1')] this is inherited from the connecitonist and should be defined by every node!
    # ports_out = [Port('port 1')]

    category = "Default"
    description = ""

    example_init = {}

    # not super awesome, but will do the trick for now:
    # have a register of clock ticks in the graph on the node class (should never be overwritten)
    # everytime a child node processes something it registers this here
    # then we can join the whole graph by waiting until in this register all ctrs are as high as the highest senders (if all senders have stopped sending)
    # ---
    # TODO: figure out how this behaves when loading the module only once, but executing the piplines twice!
    # Worst case: the state is kept and all the ctrs are wrong :/
    # I think this should be fine tho, as the logger seems to work and is the same (?!?)
    _clocks = Clock_Register()

    # === Basic Stuff =================
    def __init__(self,
                 name="Name",
                 compute_on=Location.SAME, 
                 should_time=False):
        
        super().__init__()

        self.name = name

        self.compute_on = compute_on

        for port in self.ports_in:
            print(port, type(port))

        self._received_data = {
            port.key: QueueHelperHack(compute_on=compute_on)
            # key: QueueHelperHack(compute_on=Location.THREAD)
            for port in self.ports_in
        }

        self._ctr = None

        self._running = False

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

        self._perf_user_fn = Time_Per_Call()
        self._perf_framework = Time_Between_Call()
        if should_time:
            self._call_user_fn_process = partial(self._perf_framework.call_fn, partial(self._perf_user_fn.call_fn, self._call_user_fn))
        else:
            self._call_user_fn_process = self._call_user_fn

    def __repr__(self):
        return str(self)
        # return f"{str(self)} Settings:{json.dumps(self._serialize())}"

    def __str__(self):
        return f"{self.name} [{self.__class__.__name__}]"


    # === Connection Stuff =================
    def add_input(self, emit_node: 'Node', emit_port:Port, recv_port:Port):
        if not isinstance(emit_node, Node):
            raise ValueError("Emitting Node must be of instance Node. Got:",
                             emit_node)
        return super().add_input(emit_node, emit_port, recv_port)

    # # === Subclass Validation Stuff =================
    # def __init_subclass__(self):
    #     """
    #     Check if a new class instance is valid, ie if channels are correct, info is existing etc
    #     """
    #     pass
    
    # TODO: actually start, ie design/test a sending node!
    # === Start/Stop Stuff =================
    def _get_start_nodes(self):
        # TODO: this should not be ports_in, but channels connected!
        # self._is_input_connected
        # return list(filter(lambda x: len(x.ports_in) == 0, self.discover_graph(self)))
        return list(filter(lambda x: len(x.ports_in) == 0, self.discover_graph(self)))

    def start(self, children=True, join=False):
        self.spawn_processes()
        
        start_nodes = self._get_start_nodes()
        print(start_nodes)
        for i, node in enumerate(start_nodes):
            print('Starting:', node, join, i + 1 == len(start_nodes), children)
            node.start_node(children=children, join=join and i + 1 == len(start_nodes))

    def stop(self, children=True):
        start_nodes = self._get_start_nodes()
        print(start_nodes)
        for node in start_nodes:
            print("Stopping:", node, children)
            node.stop_node(children=children)

    def _call_user_fn(self, _fn, _fn_name, *args, **kwargs):
        try:
            return _fn(*args, **kwargs)
        except Exception as e:
            self.error(f'failed to execute {_fn_name}')
            self.error(e) # TODO: add stack trace?
            self.error(traceback.format_exc())
    
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


    def start_node(self, children=True, join=False):
        if self._running == False:  # the node might be child to multiple parents, but we just want to start once
            # first start children, so they are ready to receive inputs
            # children cannot not have inputs, ie they are always relying on this node to send them data if they want to progress their clock
            if children:
                for con in self.output_connections:
                    con._receiving_node.start_node()

            # now start self
            self._running = True

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

        if join:
            self._join()
        else:
            self._clocks.set_passthrough(self)

    def stop_node(self, children=True):
        # first stop self, so that non-running children don't receive inputs
        if self._running == True:  # the node might be child to multiple parents, but we just want to stop once
            self.info('Stopping')
            self._running = False

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
            self.info('Stopped')

            # now stop children
            if children:
                for con in self.output_connections:
                    con._receiving_node.stop_node()

    def _join(self):
        # blocks until all nodes in the graph reached the same clock as the node we are calling this from
        # for senders: this only makes sense for senders with block=True as otherwise race conditions might make this return before the final data was send
        # ie in the extreme case: self._ctr=0 and all others as well
        self_name = str(self)
        # the first part will be false until the first time _process() is being called, after that, the second part will be false until all clocks have catched up to our own
        while (not self_name in self._clocks.read_state()[0]) or not (
                self._clocks.all_at(max(self._clocks.state[self_name]))):
            time.sleep(0.01)
        self.info(
            f'Join returned at clock {max(self._clocks.state[self_name])}')

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

    # === Data Stuff =================
    def _emit_data(self, data, channel: Port = None, ctr: int = None):
        """
        Called in computation process, ie self.process
        Emits data to childs, ie child.receive_data
        """
        if channel is None:
            channel = list(self.ports_out._asdict().values())[0]
        channel = channel.key
        clock = self._ctr if ctr is None else ctr

        for con in self.output_connections:
            if con._emit_port.key == channel:
                con._receiving_node.receive_data(
                    clock, payload={con._recv_port.key: data})

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

    def _retrieve_current_data(self, ctr):
        res = {}
        # update current state, based on own clock
        for key, queue in self._received_data.items():
            # discard everything, that was before our own current clock
            found_value, cur_value = queue.get(ctr)
            self.verbose('retreiving current data', key, found_value,
                         queue._read.keys(), ctr)
            if found_value:
                # TODO: instead of this key transformation/tolower consider actually using classes for data types... (allows for gui names alongside dev names and not converting between the two)
                res[key] = cur_value
        return res

    # Most of the time when we already receive data from the next tick of some of the inputs AND the current tick would not be processed, we are likely to want to skip the tick where data was missing
    # basically: if a frame was dropped before this node, we will also drop it and not block
    # def discard_previous_tick(self, ctr):
    #     res = bool(self._retrieve_current_data(ctr=ctr + 1))
    #     if res:
    #         self.debug('cur tick data:', self._retrieve_current_data(ctr=ctr).keys())
    #         self.debug('next tick data:', self._retrieve_current_data(ctr=ctr + 1).keys())
    #     return False

    def _report_perf(self):
        processing_duration = self._perf_user_fn.average()
        invocation_duration = self._perf_framework.average()
        self.debug(f'Processing: {processing_duration * 1000:.5f}ms; Time between calls: {(invocation_duration - processing_duration) * 1000:.5f}ms; Time between invocations: {invocation_duration * 1000:.5f}ms')

    def _process(self, ctr):
        """
        called in location of self
        called every time something is put into the queue / we received some data (ie if there are three inputs, we expect this to be called three times, before the clock should advance)
        """
        self.verbose('_Process triggered')

        # update current state, based on own clock
        _current_data = self._retrieve_current_data(ctr=ctr)

        # check if all required data to proceed is available and then call process
        # then cleanup aggregated data and advance our own clock
        if self._should_process(**_current_data):
            self.debug('Decided to process', ctr, _current_data.keys())
            # yes, ```if self.process``` is shorter, but as long as the documentation isn't there this is also very clear on the api
            # prevent_tick = self.process(**_current_data)
            # IMPORTANT: this is possible, due to the fact that only sender and syncs have their own clock
            # sender will never receive inputs and therefore will never have
            # TODO: IMPORTANT: every node it's own clock seems to have been a mistake: go back to the original idea of "senders and syncs implement clocks and everyone else just passes them along"
            self._ctr = ctr
            self._call_user_fn_process(self.process, 'process', **_current_data, _ctr=ctr)
            self.verbose('process fn finished')
            self._report_perf()
            for queue in self._received_data.values():
                queue.discard_before(ctr)

            # self.verbose('discarded values, registering now', self._clocks._store.is_set())

            self._clocks.register(str(self), ctr)
            # if not keep_current_data:
            #     self.discard_before
            # if not prevent_tick:
            # else:
            #     self.debug('Prevented tick')
        else:
            self.verbose('Decided not to process', ctr, _current_data.keys())
        self.verbose('_Process finished')

    def trigger_process(self, ctr):
        if self.compute_on in [Location.SAME]:
            # same and threads both may be called directly and do not require a notification
            self._process(ctr)
        elif self.compute_on in [Location.PROCESS, Location.THREAD]:
            # Process and thread both activley wait on the _received_data queues and therefore do not require an active trigger to process
            pass
        else:
            raise Exception(f'Location {self.compute_on} not implemented yet.')

    def receive_data(self, ctr, payload):
        """
        called in location of emitting node
        """
        # store all received data in their according mp.simplequeues
        for key, val in payload.items():
            self.error(f'Received: "{key}" with clock {ctr}')
            self._received_data[key].put(ctr, val)

        # FIX ME! TODO: this is a pain in the butt
        # Basically:
        # 1. node A runs in a thread
        # 2. node B runs on another thread
        # 3. A calls emit_data in its own process()
        # 4. this triggers a call of B.receive_data, but in the context of As thread
        # which means, that suddently B is not running in another thread, but this one.
        # this clashes if b also waits for an input from yet another thread
        # mainly this also means, that the QueueHelper hack reads from it's queues at different threads and therefore cannot combine the information
        # not sure how to fix this though :/ for now: we'll just not execute anything in Location.SAME and fix this later
        self.trigger_process(ctr)

    # === Performance Stuff =================
    # def timeit(self):
    #     pass

    # TODO: Look at the original timing code, ideas and plots

    ## TODO: this is an absolute hack. remove! consider how to do this, maybe consider the pickle/sklearn interfaces?
    def _set_attr(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

    # === Node Specific Stuff =================
    # (Computation, Render)
    # TODO: consider changing this to follow the pickle conventions
    def _settings(self):
        return {"name": self.name}

    def _should_process(self, **kwargs):
        """
        Given the inputs, this determines if process should be called on the new data or not
        params: **ports_in
        returns bool (if process should be called with these inputs)
        """
        return set([x.key for x in self.ports_in]) <= set(list(kwargs.keys()))

    def process_time_series(self, ts):
        return ts

    def process(self, data, **kwargs):
        """
        Heart of the nodes processing, should be a stateless(/functional) processing function, 
        ie "self" should only be used to call _emit_[data|draw]. 
        However, if you really require a separate state management of your own, you may use self

        TODO: consider later on if we might change this to not call _emit but just return the stuff needed...
        -> pro: clearer process functions, more likely to actually be funcitonal; cannot have confusion when emitting twice in the same channel
        -> con: children need to wait until the full node is finished with processing (ie: no ability to do partial computations (not sure if we want those, tho))

        params: **ports_in
        returns None
        """
        res = list(map(self.process_time_series, data))
        self._emit_data(res)

    def _onstart(self):
        """
        executed on start, should return! (if you need always running -> blockingSender)
        """
        pass

    def _onstop(self):
        """
        executed on stop, should return! (if you need always running -> blockingSender)
        """
        pass

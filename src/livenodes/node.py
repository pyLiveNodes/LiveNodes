from functools import partial
import numpy as np
import time
import queue
import traceback

from .clock_register import Clock_Register
from .perf import Time_Per_Call, Time_Between_Call
from .port import Port

from .node_connector import Connectionist
from .node_logger import Logger
from .node_serializer import Serializer
from .processor import Processor, Location # location is imported here, as we'll need to update all the from livenodes.nodes import location soon


class Node(Connectionist, Processor, Logger, Serializer):
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
                 should_time=False,
                 **kwargs):
        
        self.name = name
        super().__init__(**kwargs)

        self.output_bridges = {}

        for port in self.ports_in:
            print(port, type(port))

        self._ctr = None

        self._running = False 

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
        super().spawn_processes()
        
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
    

    def start_node(self, children=True, join=False):
        if self._running == False:  # the node might be child to multiple parents, but we just want to start once
            # first start children, so they are ready to receive inputs
            # children cannot not have inputs, ie they are always relying on this node to send them data if they want to progress their clock
            if children:
                for con in self.output_connections:
                    con._recv_node.start_node()

            # now start self
            self._running = True

            super().start_node()

        # TODO: remove this? / consider in which cases we need the option to join and in which we dont...
        if join:
            self._join()
        else:
            self._clocks.set_passthrough(self)

    def stop_node(self, children=True):
        # first stop self, so that non-running children don't receive inputs
        if self._running == True:  # the node might be child to multiple parents, but we just want to stop once
            self.info('Stopping')
            self._running = False

            super().stop_node()
            
            self.info('Stopped')

            # now stop children
            if children:
                for con in self.output_connections:
                    con._recv_node.stop_node()

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
                con._recv_node.receive_data(
                    clock, con, data)

    def receive_data(self, ctr, connection, data):
        """
        called in location of emitting node
        """
        # store all received data in their according mp.simplequeues
        self.error(f'Received: "{connection._recv_port.key}" with clock {ctr}')
        # self._received_data[key].put(ctr, val)
        # this is called in the context of the emitting node, the data storage is then in charge of using the right means of transport, such that the process triggered has the available data in the same context as the receiving node's process is called
        self.data_storage.put(connection, ctr, data)
        self.trigger_process(ctr)

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
        _current_data = self.data_storage.get(ctr=ctr)

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
            self.data_storage.discard_before(ctr)

            # self.verbose('discarded values, registering now', self._clocks._store.is_set())

            self._clocks.register(str(self), ctr)
        else:
            self.verbose('Decided not to process', ctr, _current_data.keys())
        self.verbose('_Process finished')

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

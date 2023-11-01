import asyncio
from functools import partial
import multiprocessing as mp
import pathlib
import numpy as np
import traceback

from .components.utils.perf import Time_Per_Call, Time_Between_Call
from .components.port import Port
from .components.utils.reportable import Reportable

from .components.node_connector import Connectionist
from .components.node_logger import Logger
from .components.node_serializer import Serializer
from .components.bridges import Multiprocessing_Data_Storage

INSTALL_LOC = str(pathlib.Path(__file__).parent.resolve())
    

class Node(Connectionist, Logger, Serializer):
    # === Information Stuff =================
    # ports_in = [Port('port 1')] this is inherited from the connecitonist and should be defined by every node!
    # ports_out = [Port('port 1')]

    category = "Default"
    description = ""

    example_init = {}

    # === Basic Stuff =================
    def __init__(self,
                 name="Name",
                 should_time=False,
                 compute_on="",
                 **kwargs):
        
        super().__init__(name=name, **kwargs)

        reserved_sequences = ['->', '[', ']', '.']
        if any(ext in name for ext in reserved_sequences):
            raise ValueError(f'Node name must not contain any of the following: {reserved_sequences}, got: {name}')

        self.should_time = should_time
        self.compute_on = compute_on
        self.bridge_listeners = []

        self.locked = mp.Event()

        self._ctr = None

        self._n_stop_calls = 0

        self._perf_user_fn = Time_Per_Call()
        self._perf_framework = Time_Between_Call()

        if should_time:
            self._call_user_fn_process = partial(self._perf_framework.call_fn, partial(self._perf_user_fn.call_fn, self._call_user_fn))
        else:
            self._call_user_fn_process = self._call_user_fn

        # Fix this on creation such that we can still identify a node if it was pickled into another (spawned) process
        self._id_ = id(self)

        self.ret_accumulated = None


    def __repr__(self):
        return str(self)
        # return f"{str(self)} Settings:{json.dumps(self._serialize())}"

    def __hash__(self) -> int:
        return id(self)

    # === Connection Stuff =================
    def add_input(self, emit_node: 'Node', emit_port:Port, recv_port:Port):
        if not isinstance(emit_node, Node):
            raise ValueError("Emitting Node must be of instance Node. Got:",
                             emit_node)
        
        if not emit_port.can_input_to(recv_port):
            self.info(recv_port.accepts_inputs(emit_port.example_values))
            raise ValueError(f'Port {str(emit_port)} cannot input into {str(recv_port)}')
        
        return super().add_input(emit_node, emit_port, recv_port)

    # # === Subclass Validation Stuff =================
    def __init_subclass__(self, abstract_class=False):
        """
        Check if a new class instance is valid, ie if channels are correct, info is existing etc
        """
        if not abstract_class:
            ### check if ports where set correctly
            if self.ports_in is None:
                raise Exception('Class is required to define input ports.')
            else:
                for p in self.ports_in:
                    if (not isinstance(p, Port)) or (p.__class__ == Port):
                        raise Exception('Input ports must be subclasses of port. Got: ', p.__class__, p)

            if self.ports_out is None:
                raise Exception('Class is required to define output ports.')
            else:
                for p in self.ports_out:
                    if (not isinstance(p, Port)) or (p.__class__ == Port):
                        raise Exception('Output ports must be subclasses of port. Got: ', p.__class__, p)
        # if len(self.ports_in.example_values) <= 0:
        #     raise Exception('Ports likely still set to default')
        # else:
        #     # check if check_value is implemented -> also a good way to know if Port instead of a subclass is used
        #     for val in self.ports_in.example_values:
        #         self.ports_in.check_value(val)
            

    
    def _call_user_fn(self, _fn, _fn_name, *args, **kwargs):
        try:
            return _fn(*args, **kwargs)
        except Exception as e:
            self.error(f'failed to execute {_fn_name}')
            self.error(e)
            self.error(traceback.format_exc())


    # === API for Computers =================
    
    # no further inputs, outputs or settings changes are allowed and we will resolve connections
    # TODO: actually lock those ressources
    # _main thread
    def lock(self):
        self.info('Locking')
        self.locked.set()

        self.info('Resolving Bridges')
        send_endpoint_pairs = []
        recv_endpoint_pairs = []

        for con in self.input_connections:
            send_endpoint, recv_endpoint = Multiprocessing_Data_Storage.resolve_bridge(con)
            send_endpoint_pairs.append((con, send_endpoint))
            recv_endpoint_pairs.append((con, recv_endpoint))
        
        self.info('Ready to proceed with run calls')
        # self.error('unique send bridges', np.unique([str(b[1]) for b in send_endpoint_pairs], return_counts=True))
        # self.error('unique recv bridges', np.unique([str(b[1]) for b in recv_endpoint_pairs], return_counts=True))
        
        return send_endpoint_pairs, recv_endpoint_pairs

    # _computer thread
    # here inputs are the endpoints we receive data from and outputs are the endpoints we send data through
    def ready(self, input_endpoints=None, output_endpoints=None):
        self.info('Readying')
        self.debug('unique send endpoints', [[str(b) for b in bl] for bl in output_endpoints.values()])
        self.debug('unique recv endpoints', [str(b) for b in input_endpoints.values()])
        
        self.data_storage = Multiprocessing_Data_Storage(input_endpoints, output_endpoints)

        if not self.locked.is_set():
            self.error('Forgot to lock node')
            raise Exception('Node was not locked and no inputs where set')

        self._loop = asyncio.get_event_loop()
        self._finished = self._loop.create_future()
        if len(self.input_connections) > 0:
            self._bridges_closed = self._loop.create_task(self.data_storage.on_all_closed())
            self._bridges_closed.add_done_callback(self._finish)
        else:
            self.info("Node has no input connections, please make sure it calls self._finish once it's done")
        self._setup_process()

        return self._finished

    # _computer thread
    def start(self):
        self.info('Starting')
        # TODO: not sure about this yet: seems uneccessary if we have the ready anyway.. 
        # -> then again this pattern might prove quite helpful in the future, ie try to connect to some sensor and disply "waiting" until all nodes are online and we can start 
        #   -> prob. rather within the nodes.. 
        #   -> but when thinking about multiple network pcs this might make a lot of sense...
        self._onstart()

    # TODO: currently this may be called multiple times: should we change that to ensure a single call?
    # _computer thread
    def stop(self):
        self.info('Stopping')

        # TODO: not sure about this here, check the documentation!
        # cancel all remaining bridge listeners (we'll not receive any further data now anymore)
        for future in self.bridge_listeners:
            future.cancel()

        self._onstop()

    # _computer thread
    def _finish(self, task=None):
        self.info('Finishing')
        # task=none is needed for the done_callback but not used

        # close bridges telling the following nodes they will not receive input from us anymore
        for con in self.output_connections:
            self.debug('Closing', str(con))
            self.data_storage.close_bridges()

        # indicate to the node, that it now should finish wrapping up
        self.stop()

        # also indicate to parent, that we're finished
        # the note may have been finished before thus, we need to check the future before setting a result
        # -> if it finished and now stop() is called
        if not self._finished.done():
            self._finished.set_result(True)


    # _computer thread
    async def _await_input(self, queue):
        while True:
            try:
                ctr = await queue.update()
                self._process(ctr)
            except Exception as err:
                self.logger.exception(f'failed to execute _process in queue update')
                self.error(err)

    # _computer thread
    def _setup_process(self):
        self.bridge_listeners = []
        # TODO: this should not be here. Node should not now about internals of data storage (albeit, data_storage could actually be a mixin...)
        for queue in self.data_storage.in_bridges.values():
            # self.debug(str(queue))
            self.bridge_listeners.append(self._loop.create_task(self._await_input(queue)))
        self.debug(f'Found {len(self.bridge_listeners)} input bridges')

        # TODO: should we add a "on fail wrap up and tell parent" task here? ie task(wait(self.bridge_listeners, return=first_exception))


    def ret(self, **kwargs):
        return kwargs

    # optional way to accumulate returns over multiple calls
    # will reset once ret_accumulated is called in the end
    def ret_accu(self, value, port):
        if self.ret_accumulated is None:
            def h(**kwargs):
                nonlocal self
                self.ret_accumulated = None
                return self.ret(**kwargs)
            self.ret_accumulated = h
        self.ret_accumulated = partial(self.ret_accumulated, **{port.key: value})


    # === Data Stuff =================
    def _emit_data(self, data, channel: Port = None, ctr: int = None):
        """
        Called in computation process, ie self.process
        Emits data to childs, ie child.receive_data
        """
        # TODO: consider how to handle this:
        # basically: i would like every node to pass data via returns
        # however, in some producer cases (also biokit train status cases), returns are not feasible but emit must be called directly
        # not sure how to handle that...
        # parent_caller = inspect.getouterframes( inspect.currentframe() )[1]
        # if not parent_caller.filename.startswith(INSTALL_LOC):
        #     print('parent', parent_caller.filename)
        #     self.warn('_emit_data should only be called by nodes directly if they know what they ')

        if channel is None:
            channel = list(self.ports_out._asdict().values())[0].key
        elif isinstance(channel, Port):
            channel = channel.key
        elif type(channel) == str:
            # self.info(f'Call by str will be deprecated, got: {channel}', [p.key for p in self.ports_out])
            if channel not in [p.key for p in self.ports_out]: 
                #._fields:
                raise ValueError(f'Unknown Port {str(self)}.{channel}')
                
        clock = self._ctr if ctr is None else ctr

        if __debug__:
            # checks if the sent data adhere to the set port type
            val_ok, msg = self.get_port_out_by_key(channel).check_value(data)
            assert val_ok, f"Error: {msg}; On channel: {str(self)}.{channel}"

        self.debug('Emitting', channel, clock, ctr, self._ctr, np.array(data).shape)
        self.data_storage.put(channel, clock, data)


    def _process(self, ctr):
        """
        called in location of self
        called every time something is put into the queue / we received some data (ie if there are three inputs, we expect this to be called three times, before the clock should advance)
        """
        self.debug('_Process triggered')
        assert (self._ctr is None) or (self._ctr <= ctr), "Ctr already processed"

        # update current state, based on own clock
        _current_data = self.data_storage.get(ctr=ctr)

        # Considered to type check here as well, but not necessary, as every data that arrives here must be the type it was sent
        # and connections should only be allowed between compatible types

        # sure?
        self._report(current_state = {"ctr": ctr, "data": _current_data})

        # check if all required data to proceed is available and then call process
        # then cleanup aggregated data and advance our own clock
        if self._should_process(**_current_data):
            self.debug('Decided to process', ctr, _current_data.keys())
            self._ctr = ctr
            emit_data = self._call_user_fn_process(self.process, 'process', **_current_data, _ctr=ctr)
            if emit_data is not None:
                emit_ctr = None
                if type(emit_data) == tuple:
                    emit_data, emit_ctr = emit_data
                for key, val in emit_data.items():
                    self._emit_data(data=val, channel=key, ctr=emit_ctr)
            self.debug('process fn finished')
            self._report(node = self) # for latency and calc reasons
            self.data_storage.discard_before(ctr)
        else:
            self.debug('Decided not to process', ctr, _current_data.keys())
        self.debug('_Process finished')

    # === Performance Stuff =================
    # def timeit(self):
    #     pass

    # TODO: Look at the original timing code, ideas and plots

    ## TODO: this is an absolute hack. remove! consider how to do this, maybe consider the pickle/sklearn interfaces?
    def _set_attr(self, **kwargs):
        # make sure the names are unique when being set
        if 'name' in kwargs:
            if not self.is_unique_name(kwargs['name']):
                kwargs['name'] = self.create_unique_name(kwargs['name'])

        # set values (again, we need a more specific idea of how node states and setting changes should look like!)
        for key, val in kwargs.items():
            setattr(self, key, val)

        # return the finally set values (TODO: should this be explizit? or would it be better to expect that params might not by finally set as passed?)
        return kwargs

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

    # TODO: does this hold up for anything except the "standard" Data stream?
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
        self.ret_accu(list(map(self.process_time_series, data)), port=self.ports_out[0])
        return self.ret_accumulated()

    def _onstart(self):
        """
        executed on start
        """
        pass

    def _onstop(self):
        """
        executed on stop
        """
        pass

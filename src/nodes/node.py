
from enum import Enum
import json
from re import L
from socket import timeout
import numpy as np
import time 
import multiprocessing as mp
import queue
from collections import defaultdict
import datetime
import threading

# this fix is for macos (https://docs.python.org/3.8/library/multiprocessing.html#contexts-and-start-methods) 
# TODO: test/validate this works in all cases (ie increase test cases, coverage and machines to be tested on) 
mp.set_start_method('fork')

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)

class Location(Enum):
    SAME = 1
    THREAD = 2
    PROCESS = 3
    # SOCKET = 4

class Canvas(Enum):
    MPL = 1
    # QT = 2

class QueueHelperHack():
    def __init__(self):
        self.queue = mp.SimpleQueue()
        self._read = {}

    def put(self, ctr, item):
        self.queue.put((ctr, item))

    def get(self, ctr, discard_before=True):
        while not self.queue.empty():
            itm_ctr, item = self.queue.get()
            self._read[itm_ctr] = item

        if ctr in self._read:
            res = self._read[ctr]
            
            if discard_before:
                self._read = {key: val for key, val in self._read.items() if key > ctr}
                
            return True, res
        return False, None
    

class Clock():
    def __init__(self, node, should_time):
        self.ctr = 0
        self.times = []
        self.node = node

        if should_time:
            self.tick = self._tick_with_time
        else:
            self.tick = self._tick
    
    def _tick_with_time(self):
        self.ctr += 1
        self.times.append(time.time())

    def _tick(self):
        self.ctr += 1

class Connection ():
    # TODO: consider creating a channel registry instead of using strings?
    def __init__(self, emitting_node, receiving_node, emitting_channel="Data", receiving_channel="Data", connection_counter=0):
        self._emitting_node = emitting_node
        self._receiving_node = receiving_node
        self._emitting_channel = emitting_channel
        self._receiving_channel = receiving_channel
        self._connection_counter = connection_counter

    def __repr__(self):
        return f"{str(self._emitting_node)}.{self._emitting_channel} -> {str(self._receiving_node)}.{self._receiving_channel}"

    def to_json(self):
        return json.dumps({"emitting_node": self._emitting_node, "receiving_node": self._receiving_node, "emitting_channel": self._emitting_channel, "receiving_channel": self._receiving_channel, "connection_counter": self._connection_counter})

    def _set_connection_counter(self, counter):
        self._connection_counter = counter

    def _similar(self, other):
        return self._emitting_node == other._emitting_node and \
            self._receiving_node == other._receiving_node and \
            self._emitting_channel == other._emitting_channel and \
            self._receiving_channel == other._receiving_channel

    def __eq__(self, other):
        return self._similar(other) and self._connection_counter == other._connection_counter

# class LogLevels(Enum):
#     Debug 

LOGGER_LOCK = mp.Lock()


class Node ():
    # === Information Stuff =================
    channels_in = []
    channels_out = []

    category = "Default"
    description = ""

    example_init = {}

    canvas = Canvas.MPL

    # === Basic Stuff =================
    def __init__(self, name, compute_on=Location.SAME, should_time=False):

        self.name = name
        
        self.input_connections = []
        self.output_connections = []

        self._compute_on = compute_on

        self._received_data = {key: QueueHelperHack() for key in self.channels_in}
        self._draw_state = mp.SimpleQueue()
        self._current_data = {}

        self._clock = Clock(node=self, should_time=should_time)

        self._running = False

        self._subprocess_info = {}
        if self._compute_on in [Location.PROCESS]:
            self._subprocess_info = {
                "process": mp.Process(target=self._process_on_proc),
                "message_to_subprocess": mp.Queue(),
                "termination_lock": mp.Lock()
            }
        elif self._compute_on in [Location.THREAD]:
            self._subprocess_info = {
                "process": threading.Thread(target=self._process_on_proc),
                "message_to_subprocess": mp.Queue(),
                "termination_lock": threading.Lock()
            }

    def __repr__(self):
        return str(self)
        # return f"{str(self)} Settings:{json.dumps(self._serialize())}"

    def __str__(self):
        return f"{self.name} [{self.__class__.__name__}]"


    # === Logging Stuff =================
    # TODO: move this into it's own module/file?
    def _log(self, *text):
        # if 4 <= level:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %X")
        cur_proc = mp.current_process().name
        cur_thread = threading.current_thread().name
        level = "Debug"
        node = str(self)
        txt = " ".join(str(t) for t in text)

        msg = f"{timestamp} | {cur_proc: <11} | {cur_thread: <11} | {level: >11} | {node: >15} | {txt}"

        # acquire blocking log
        LOGGER_LOCK.acquire(True)

        print(msg, flush=True)

        # release log
        LOGGER_LOCK.release()

    # def set_log_level(self, level):
    #     self._log_level = level


    # # === Subclass Validation Stuff =================
    # def __init_subclass__(self):
    #     """
    #     Check if a new class instance is valid, ie if channels are correct, info is existing etc
    #     """
    #     pass


    # === Seriallization Stuff =================
    def copy(self, children=False, parents=False):
        """
        Copy the current node
        if deep=True copy all childs as well
        """
        # not sure if this will work, as from_json expects a cls not self...
        return self.from_json(self.to_json(children=children, parents=parents)) #, children=children, parents=parents)

    def get_settings(self):
        return { \
            "settings": self._settings(),
            "inputs": [con.to_json() for con in self.input_connections],
            "outputs": [con.to_json() for con in self.output_connections]
        }

    def to_json(self, children=False, parents=False):
        # Assume no nodes in the graph have the same name+node_class -> should be checked in the add_inputs
        res = {str(self): self.get_settings()}
        if parents:
            for node in self.discover_parents(self):
                res[str(node)] = node.get_settings()
        if children:
            for node in self.discover_childs(self):
                res[str(node)] = node.get_settings()
        return json.dumps(res, cls=NumpyEncoder)
    
    @classmethod
    def from_json(cls, json_str, initial_node=None): 
        # TODO: implement children=True, parents=True
        items = json.loads(json_str)
        # format should be as in to_json, ie a dictionary, where the name is unique and the values is a dictionary with three values (settings, ins, outs)

        items_instc = {}
        initial = None

        # first pass: create nodes
        for name, itm in items.items():
            tmp = cls(**itm['settings'])
            items_instc[name] = tmp

            if initial_node is None:
                initial = tmp

        if initial_node is not None:
            initial = items_instc[initial_node]

        # second pass: create connections
        for name, itm in items.items():
            # only add inputs, as, if we go through all nodes this automatically includes all outputs as well
            for con in itm['inputs']:
                items_instc[name].add_input(emitting_node=items_instc[con._emitting_node], emitting_channel=con._emitting_channel, receiving_channel=con._receiving_channel)

        return initial

    def save(self, path, children=True, parents=True):
        json_str = self.to_json(self, children=children, parents=parents)
        # check if folder exists?

        with open(path, 'w') as f:
            json.dump(json_str, f)

    @classmethod
    def load(cls, path):
        # TODO: implement children=True, parents=True (ie implement it in from_json)
        with open(path, 'r') as f:
            json_str = json.load(f)
        return cls.from_json(json_str)


    # === Connection Stuff =================
    def connect_inputs_to(self, emitting_node):
        """
        Add all matching channels from the emitting nodes to self as input.
        Main function to connect two nodes together with add_input.
        """

        channels_in_common = set(self.channels_in).intersection(emitting_node.channels_out)
        for channel in channels_in_common:
            self.add_input(emitting_node=emitting_node, emitting_channel=channel, receiving_channel=channel)


    def add_input(self, emitting_node, emitting_channel="Data", receiving_channel="Data"):
        """
        Add one input to self via attributes.
        Main function to connect two nodes together with connect_inputs_to
        """

        if not isinstance(emitting_node, Node):
            raise ValueError("Emitting Node must be of instance Node. Got:", emitting_node)
        
        if emitting_channel not in emitting_node.channels_out:
            raise ValueError("Emitting Channel not present on given emitting node. Got", emitting_channel)

        if receiving_channel not in self.channels_in:
            raise ValueError("Receiving Channel not present on node. Got", receiving_channel)
        
        # This is too simple, as when connecting two nodes, we really are connecting two sub-graphs, which need to be checked
        # TODO: implement this proper
        # nodes_in_graph = emitting_node.discover_full(emitting_node)
        # if list(map(str, nodes_in_graph)):
        #     raise ValueError("Name already in parent sub-graph. Got:", str(self))

        # Create connection instance
        connection = Connection(emitting_node, self, emitting_channel=emitting_channel, receiving_channel=receiving_channel)

        if len(list(filter(connection.__eq__, self.input_connections))) > 0:
            raise ValueError("Connection already exists.")

        # Find existing connections of these nodes and channels
        counter = len(list(filter(connection._similar, self.input_connections)))
        # Update counter
        connection._set_connection_counter(counter)

        # Not sure if this'll actually work, otherwise we should name them _add_output
        emitting_node._add_output(connection)
        self.input_connections.append(connection)


    def remove_input(self, emitting_node, emitting_channel="Data", receiving_channel="Data", connection_counter=0):
        """
        Remove an input from self via attributes
        """
        return self.remove_input_by_connection(Connection(emitting_node, self, emitting_channel=emitting_channel, receiving_channel=receiving_channel, connection_counter=connection_counter))
        

    def remove_input_by_connection(self, connection):
        """
        Remove an input from self via a connection
        """
        if not isinstance(connection, Connection):
            raise ValueError("Passed argument is not a connection. Got", connection)
        
        cons = list(filter(connection.__eq__, self.input_connections))
        if len(cons) == 0:
            raise ValueError("Passed connection is not in inputs. Got", connection)

        # Remove first 
        # -> in case something goes wrong on the parents side, the connection remains intact
        cons[0]._emitting_node._remove_output(cons[0]) 
        self.input_connections.remove(cons[0])


    def _add_output(self, connection):
        """
        Add an output to self. 
        Only ever called by another node, that wants this node as input
        """
        self.output_connections.append(connection)


    def _remove_output(self, connection):
        """
        Remove an output from self. 
        Only ever called by another node, that wants this node as input
        """
        cons = list(filter(connection.__eq__, self.output_connections))
        if len(cons) == 0:
            raise ValueError("Passed connection is not in inputs. Got", connection)
        self.output_connections.remove(connection)


    # TODO: actually start, ie design/test a sending node!

    # === Start/Stop Stuff =================
    def start(self, children=True):
        # first start children, so they are ready to receive inputs
        # children cannot not have inputs, ie they are always relying on this node to send them data if they want to progress their clock
        if children:
            for con in self.output_connections:
                con._receiving_node.start()

        # now start self
        if self._running == False: # the node might be child to multiple parents, but we just want to start once
            self._running = True

            # TODO: consider moving this in the node constructor, so that we do not have this nested behaviour processeses due to parents calling their childs start()
            if self._compute_on in [Location.PROCESS, Location.THREAD]:
                # self._subprocess_info['process'] = mp.Process(target=self._process_on_proc)
                self._log('create subprocess')
                self._acquire_lock(self._subprocess_info['termination_lock'])
                self._log('start subprocess')
                self._subprocess_info['process'].start()


    def stop(self, children=True):
        # first stop self, so that non-existing children don't receive inputs
        if self._running == True: # the node might be child to multiple parents, but we just want to stop once
            self._running = False

            if self._compute_on in [Location.PROCESS, Location.THREAD]:
                self._subprocess_info['termination_lock'].release()
                self._subprocess_info['process'].join(3)

                if self._compute_on in [Location.PROCESS]:
                    self._subprocess_info['process'].terminate()

        # now stop children
        if children:
            for con in self.output_connections:
                con._receiving_node.stop()

    def _acquire_lock(self, lock, block=True, timeout=None):
        if self._compute_on in [Location.PROCESS]:
            return lock.acquire(block=block, timeout=timeout)
        elif self._compute_on in [Location.THREAD]:
            if block:
                return lock.acquire(blocking=True, timeout=-1 if timeout is None else timeout)
            else:
                return lock.acquire(blocking=False) # forbidden to specify timeout
        else:
            raise Exception('Cannot acquire lock in non multi process/threading environment')


    # === Data Stuff =================
    def _emit_data(self, data, channel="Data"):
        """
        Called in computation process, ie self.process
        Emits data to childs, ie child.receive_data
        """
        for con in self.output_connections:
            if con._receiving_channel == channel:
                con._receiving_node.receive_data(self._clock, payload={channel: data})

    def _emit_draw(self, **kwargs):
        """
        Called in computation process, ie self.process
        Emits data to draw process, ie draw_inits update fn
        """
        self._draw_state.put(kwargs)

    def _process_on_proc(self):
        self._log('Started subprocess')

        # as long as we do not receive a termination signal, we will wait for data to be processed
        # the .empty() is not reliable (according to the python doc), but the best we have at the moment
        while not self._acquire_lock(self._subprocess_info['termination_lock'], block=False) or not self._subprocess_info['message_to_subprocess'].empty():
            # block until signaled that we have new data
            # as we might receive not data after having received a termination
            #      -> we'll just poll, so that on termination we do terminate after no longer than 0.1seconds
            try:
                self._subprocess_info['message_to_subprocess'].get(block=True, timeout=0.1)
            except queue.Empty:
                continue

            self._log('processing')
            self._process()

        self._log('Finished subprocess')
        
    @staticmethod
    def _channel_name_to_key(name):
        return name.replace(' ', '_').lower()
            
    def _process(self):
        """
        called in location of self
        """
        # update current state, based on own clock
        for key, queue in self._received_data.items():
            # discard everything, that was before our own current clock
            found_value, cur_value = queue.get(self._clock.ctr)
            if found_value:
                # TODO: instead of this transformation consider actually using classes for data types...
                self._current_data[self._channel_name_to_key(key)] = cur_value

        self._log(self._current_data, self._clock.ctr)
        # check if all required data to proceed is available and then call process
        # then cleanup aggregated data and advance our own clock
        if self._should_process(**self._current_data):
            self.process(**self._current_data)
            self._current_data = {}
            self._clock.tick()
        else:
            self._log('Decided not to process', self._current_data)

    def trigger_process(self):
        if self._compute_on in [Location.SAME]:
            # same and threads both may be called directly and do not require a notification
            self._process()
        elif self._compute_on in [Location.PROCESS, Location.THREAD]:
            # signal subprocess that new data has arrived by adding an item to the signal queue, 
            self._subprocess_info['message_to_subprocess'].put(1)
        else:
            raise Exception(f'Location {self._compute_on} not implemented yet.')

    def receive_data(self, clock, payload):
        """
        called in location of emitting node
        """
        # store all received data in their according mp.simplequeues
        for key, val in payload.items():
            self._received_data[key].put(clock.ctr, val)

        self.trigger_process()

    # === Connection Discovery Stuff =================
    @staticmethod
    def remove_discovered_duplicates(nodes):
        return list(set(nodes))

    @staticmethod
    def discover_childs(node):
        if len(node.output_connections) > 0:
            childs = [con._receiving_node.discover_childs(con._receiving_node) for con in node.output_connections]
            return [node] + list(np.concatenate(childs))
        return [node]

    @staticmethod
    def discover_parents(node):
        if len(node.input_connections) > 0:
            parents = [con._emitting_node.discover_parents(con._emitting_node) for con in node.input_connections]
            return [node] + list(np.concatenate(parents))
        return [node]

    @staticmethod
    def discover_full(node):
        return node.remove_discovered_duplicates(node.discover_parents(node) + node.discover_childs(node))

    def is_child_of(self, node):
        # self is always a child of itself
        return self in self.discover_childs(node)

    def is_parent_of(self, node):
        # self is always a parent of itself
        return self in self.discover_parents(node)


    # === Drawing Graph Stuff =================
    def dot_graph(self, nodes, name=False, transparent_bg=False):
        # Imports are done here, as if you don't need the dotgraph it should not be required to start
        from graphviz import Digraph
        from PIL import Image
        from io import BytesIO

        graph_attr={"size":"10,10!", "ratio":"fill"}
        if transparent_bg: graph_attr["bgcolor"]= "#00000000"
        dot = Digraph(format = 'png', strict = False, graph_attr=graph_attr)

        for node in nodes:
            shape = 'rect'
            if node.has_inputs == False:
                shape = 'invtrapezium'
            if node.has_outputs == False:
                shape = 'trapezium'
            disp_name = node.name if name else str(node)
            dot.node(str(node), disp_name, shape = shape, style = 'rounded')
        
        # Second pass: add edges based on output links
        for node in nodes:
            for node_output, _, stream_name, _ in node.output_classes:
                stream_name = 'Data' if stream_name == None else stream_name
                dot.edge(str(node), str(node_output), label=stream_name)

        return Image.open(BytesIO(dot.pipe()))

    def dot_graph_childs(self, **kwargs):
        return self.dot_graph(self.discover_childs(self), **kwargs)

    def dot_graph_parents(self, **kwargs):
        return self.dot_graph(self.discover_parents(self), **kwargs)

    def dot_graph_full(self, **kwargs):
        return self.dot_graph(self.discover_full(self), **kwargs)
    

    # === Performance Stuff =================
    # def timeit(self):
    #     pass

    # TODO: Look at the original timing code, ideas and plots


    # === Node Specific Stuff =================
    # (Computation, Render)
    # TODO: consider changing this to follow the pickle conventions
    def _settings(self):
        return {"name": self.name}

    def _should_process(self, **kwargs):
        """
        Given the inputs, this determines if process should be called on the new data or not
        params: **channels_in
        returns bool (if process should be called with these inputs)
        """
        return set(list(map(self._channel_name_to_key, self.channels_in))) <= set(list(kwargs.keys()))
    
    def process(self):
        """
        Heart of the nodes processing, should be a stateless(/functional) processing function, 
        ie "self" should only be used to call _emit_[data|draw]. 
        However, if you really require a separate state management of your own, you may use self

        TODO: consider later on if we might change this to not call _emit but just return the stuff needed...
        -> pro: clearer process functions, more likely to actually be funcitonal; cannot have confusion when emitting twice in the same channel
        -> con: children need to wait until the full node is finished with processing (ie: no ability to do partial computations (not sure if we want those, tho))

        params: **channels_in
        returns None
        """
        pass

    def init_draw(self):
        """
        Heart of the nodes drawing, should be a functional function
        """
        def update():
            pass

        return update

    def init_draw_mpl(self, subfigure):
        """
        Similar to init_draw, but specific to matplotlib animations
        Should be either or, not sure how to check that...
        """
        def update():
            pass

        return update



# class Transform(Node):
#     """
#     The default node.
#     Takes input and produces output
#     """
#     pass


class Sender(Node):
    """
    Loops the process function until it returns false, indicating that no more data is to be sent
    """

    channels_in = [] # must be empty!

    def __init_subclass__(cls):
        super().__init_subclass__()
        if len(cls.channels_in) > 0:
            # This is a design choice. Technically this might even be possible, but at the time of writing i do not forsee a usefull case.
            raise ValueError('Sender nodes cannot have input')

    def _run(self):
        """
        should be implemented instead of the standard process function
        should be a generator
        """
        yield False

    def _process_on_proc(self):
        self._log('Started subprocess')

        runner = self._run()
        try:
            # as long as we do not receive a termination signal and there is data, we will send data
            while not self._acquire_lock(self._subprocess_info['termination_lock'], block=False) and next(runner):
                self._clock.tick()
        except StopIteration:
                self._log('Reached end of run')
        self._log('Finished subprocess')


    def start(self, children=True):
        super().start(children)
        
        if self._compute_on in [Location.PROCESS, Location.THREAD]:
            self._subprocess_info['process'].join()
        elif self._compute_on in [Location.SAME]:
            # iterate until the generator that is run() returns false, ie no further data is to be processed
            runner = self._run()
            try:
                while next(runner):
                    self._clock.tick()
            except StopIteration:
                self._log('Reached end of run')
    


class BlockingSender(Sender):

    def _onstart(self):
        pass

    def _onstop(self):
        pass

    def _emit_data(self, data, channel="Data"):
        super()._emit_data(data, channel)
        # as we are a blocking sender / a sensore everytime we emit a sample, we advance our clock
        self._clock.tick()

    def _process_on_proc(self):
        self._log('Started subprocess')
        try:
            self._onstart()
        except KeyboardInterrupt:
            self._log('Received Termination Signal')
            self._onstop()
        self._log('Finished subprocess')

    def start(self, children=True):
        super().start(children)
        
        if self._compute_on in [Location.PROCESS, Location.THREAD]:
            self._subprocess_info['process'].join()
        elif self._compute_on in [Location.SAME]:
            self._onstart()

    def stop(self, children=True):
        # first stop self, so that non-existing children don't receive inputs
        if self._running == True: # the node might be child to multiple parents, but we just want to stop once
            self._running = False

            if self._compute_on in [Location.SAME, Location.THREAD]:
                self._onstop()
            elif self._compute_on in [Location.PROCESS]:
                self._subprocess_info['process'].terminate()

        # now stop children
        if children:
            for con in self.output_connections:
                con._receiving_node.stop()
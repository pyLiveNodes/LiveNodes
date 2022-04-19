from enum import IntEnum
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
import queue
import importlib
import sys

from .utils import logger, LogLevel

# this fix is for macos (https://docs.python.org/3.8/library/multiprocessing.html#contexts-and-start-methods)
# TODO: test/validate this works in all cases (ie increase test cases, coverage and machines to be tested on)
# mp.set_start_method('fork')


class NumpyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


class Location(IntEnum):
    SAME = 1
    THREAD = 2
    PROCESS = 3
    # SOCKET = 4


class Canvas(IntEnum):
    MPL = 1
    # QT = 2


class QueueHelperHack():

    def __init__(self, compute_on=Location.PROCESS):
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
        return self.ctr

    def _tick(self):
        self.ctr += 1
        return self.ctr


class Connection():
    # TODO: consider creating a channel registry instead of using strings?
    def __init__(self,
                 emitting_node,
                 receiving_node,
                 emitting_channel="Data",
                 receiving_channel="Data",
                 connection_counter=0):
        self._emitting_node = emitting_node
        self._receiving_node = receiving_node
        self._emitting_channel = emitting_channel
        self._receiving_channel = receiving_channel
        self._connection_counter = connection_counter

    def __repr__(self):
        return f"{str(self._emitting_node)}.{self._emitting_channel} -> {str(self._receiving_node)}.{self._receiving_channel}"

    def to_dict(self):
        return {
            "emitting_node": str(self._emitting_node),
            "receiving_node": str(self._receiving_node),
            "emitting_channel": self._emitting_channel,
            "receiving_channel": self._receiving_channel,
            "connection_counter": self._connection_counter
        }

    def _set_connection_counter(self, counter):
        self._connection_counter = counter

    def _similar(self, other):
        return self._emitting_node == other._emitting_node and \
            self._receiving_node == other._receiving_node and \
            self._emitting_channel == other._emitting_channel and \
            self._receiving_channel == other._receiving_channel

    def __eq__(self, other):
        return self._similar(
            other) and self._connection_counter == other._connection_counter


# class LogLevels(Enum):
#     Debug


class Node():
    # === Information Stuff =================
    channels_in = ["Data"]
    channels_out = ["Data"]

    category = "Default"
    description = ""

    example_init = {}

    # === Basic Stuff =================
    def __init__(self,
                 name="Name",
                 compute_on=Location.PROCESS,
                 should_time=False):

        self.name = name

        self.input_connections = []
        self.output_connections = []

        self.compute_on = compute_on

        self._received_data = {
            key: QueueHelperHack(compute_on=compute_on)
            for key in self.channels_in
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

    def __repr__(self):
        return str(self)
        # return f"{str(self)} Settings:{json.dumps(self._serialize())}"

    def __str__(self):
        return f"{self.name} [{self.__class__.__name__}]"

    # === Logging Stuff =================
    # TODO: move this into it's own module/file?
    def warn(self, *text):
        logger.warn(self._prep_log(*text))

    def info(self, *text):
        logger.info(self._prep_log(*text))

    def debug(self, *text):
        logger.debug(self._prep_log(*text))

    def verbose(self, *text):
        logger.verbose(self._prep_log(*text))

    def _prep_log(self, *text):
        node = str(self)
        txt = " ".join(str(t) for t in text)
        msg = f"{node: <40} | {txt}"
        return msg

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
        # not sure if this will work, as from_dict expects a cls not self...
        return self.from_dict(self.to_dict(
            children=children,
            parents=parents))  #, children=children, parents=parents)

    def _node_settings(self):
        return {"name": self.name, "compute_on": self.compute_on}

    def get_settings(self):
        return { \
            "class": self.__class__.__name__,
            "settings": dict(self._node_settings(), **self._settings()),
            "inputs": [con.to_dict() for con in self.input_connections],
            "outputs": [con.to_dict() for con in self.output_connections]
        }

    def to_dict(self, children=False, parents=False):
        # Assume no nodes in the graph have the same name+node_class -> should be checked in the add_inputs
        res = {str(self): self.get_settings()}
        if parents:
            for node in self.discover_parents(self):
                res[str(node)] = node.get_settings()
        if children:
            for node in self.discover_childs(self):
                res[str(node)] = node.get_settings()
        return res

    @classmethod
    def from_dict(cls, items, initial_node=None):
        # TODO: implement children=True, parents=True
        # format should be as in to_dict, ie a dictionary, where the name is unique and the values is a dictionary with three values (settings, ins, outs)

        items_instc = {}
        initial = None

        # first pass: create nodes
        for name, itm in items.items():
            # HACK! TODO: fix this proper
            # this whole import thing here is a huge hack, there should be a registry or something similar!
            module_name = f"src.nodes.{itm['class'].lower()}"
            if module_name not in sys.modules:
                module = importlib.import_module(module_name)
            else:
                module = importlib.reload(sys.modules[module_name])
            tmp = (getattr(module, itm['class'])(**itm['settings']))

            items_instc[name] = tmp

            # assume that the first node without any inputs is the initial node...
            if initial_node is None and len(tmp.channels_in) <= 0:
                initial_node = name

        # not sure if we can remove this at some point...
        if initial_node is not None:
            initial = items_instc[initial_node]

        # second pass: create connections
        for name, itm in items.items():
            # only add inputs, as, if we go through all nodes this automatically includes all outputs as well
            for con in itm['inputs']:
                items_instc[name].add_input(
                    emitting_node=items_instc[con["emitting_node"]],
                    emitting_channel=con['emitting_channel'],
                    receiving_channel=con['receiving_channel'])

        return initial

    def save(self, path, children=True, parents=True):
        json_str = self.to_dict(children=children, parents=parents)
        # check if folder exists?

        with open(path, 'w') as f:
            json.dump(json_str, f, cls=NumpyEncoder, indent=2)

    @classmethod
    def load(cls, path):
        # TODO: implement children=True, parents=True (ie implement it in from_dict)
        with open(path, 'r') as f:
            json_str = json.load(f)
        return cls.from_dict(json_str)

    # === Connection Stuff =================
    def connect_inputs_to(self, emitting_node):
        """
        Add all matching channels from the emitting nodes to self as input.
        Main function to connect two nodes together with add_input.
        """

        channels_in_common = set(self.channels_in).intersection(
            emitting_node.channels_out)
        for channel in channels_in_common:
            self.add_input(emitting_node=emitting_node,
                           emitting_channel=channel,
                           receiving_channel=channel)

    def add_input(self,
                  emitting_node,
                  emitting_channel="Data",
                  receiving_channel="Data"):
        """
        Add one input to self via attributes.
        Main function to connect two nodes together with connect_inputs_to
        """

        if not isinstance(emitting_node, Node):
            raise ValueError("Emitting Node must be of instance Node. Got:",
                             emitting_node)

        if emitting_channel not in emitting_node.channels_out:
            raise ValueError(
                f"Emitting Channel not present on given emitting node ({str(emitting_node)}). Got",
                emitting_channel)

        if receiving_channel not in self.channels_in:
            raise ValueError(
                f"Receiving Channel not present on node ({str(self)}). Got",
                receiving_channel)

        # This is too simple, as when connecting two nodes, we really are connecting two sub-graphs, which need to be checked
        # TODO: implement this proper
        # nodes_in_graph = emitting_node.discover_full(emitting_node)
        # if list(map(str, nodes_in_graph)):
        #     raise ValueError("Name already in parent sub-graph. Got:", str(self))

        # Create connection instance
        connection = Connection(emitting_node,
                                self,
                                emitting_channel=emitting_channel,
                                receiving_channel=receiving_channel)

        if len(list(filter(connection.__eq__, self.input_connections))) > 0:
            raise ValueError("Connection already exists.")

        # Find existing connections of these nodes and channels
        counter = len(list(filter(connection._similar,
                                  self.input_connections)))
        # Update counter
        connection._set_connection_counter(counter)

        # Not sure if this'll actually work, otherwise we should name them _add_output
        emitting_node._add_output(connection)
        self.input_connections.append(connection)

    def remove_all_inputs(self):
        for con in self.input_connections:
            self.remove_input_by_connection(con)

    def remove_input(self,
                     emitting_node,
                     emitting_channel="Data",
                     receiving_channel="Data",
                     connection_counter=0):
        """
        Remove an input from self via attributes
        """
        return self.remove_input_by_connection(
            Connection(emitting_node,
                       self,
                       emitting_channel=emitting_channel,
                       receiving_channel=receiving_channel,
                       connection_counter=connection_counter))

    def remove_input_by_connection(self, connection):
        """
        Remove an input from self via a connection
        """
        if not isinstance(connection, Connection):
            raise ValueError("Passed argument is not a connection. Got",
                             connection)

        cons = list(filter(connection.__eq__, self.input_connections))
        if len(cons) == 0:
            raise ValueError("Passed connection is not in inputs. Got",
                             connection)

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
            raise ValueError("Passed connection is not in outputs. Got",
                             connection)
        self.output_connections.remove(connection)

    def _is_input_connected(self, receiving_channel='Data'):
        return any([
            x._receiving_channel == receiving_channel
            for x in self.input_connections
        ])

    # TODO: actually start, ie design/test a sending node!

    # === Start/Stop Stuff =================
    def start(self, children=True):
        if self._running == False:  # the node might be child to multiple parents, but we just want to start once
            # first start children, so they are ready to receive inputs
            # children cannot not have inputs, ie they are always relying on this node to send them data if they want to progress their clock
            if children:
                for con in self.output_connections:
                    con._receiving_node.start()

            # now start self
            self._running = True

            # TODO: consider moving this in the node constructor, so that we do not have this nested behaviour processeses due to parents calling their childs start()
            if self.compute_on in [Location.PROCESS, Location.THREAD]:
                if self.compute_on == Location.PROCESS:
                    self._subprocess_info['process'] = mp.Process(
                        target=self._process_on_proc)
                elif self.compute_on == Location.THREAD:
                    self._subprocess_info['process'] = threading.Thread(
                        target=self._process_on_proc)

                self.info('create subprocess')
                self._acquire_lock(self._subprocess_info['termination_lock'])
                self.info('start subprocess')
                self._subprocess_info['process'].start()
            elif self.compute_on in [Location.SAME]:
                self._onstart()
                self.info('Executed _onstart')

    def stop(self, children=True):
        # first stop self, so that non-existing children don't receive inputs
        if self._running == True:  # the node might be child to multiple parents, but we just want to stop once
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
                self._onstop()
            self.info('Stopped')

            # now stop children
            if children:
                for con in self.output_connections:
                    con._receiving_node.stop()

    def _acquire_lock(self, lock, block=True, timeout=None):
        if self.compute_on in [Location.PROCESS]:
            return lock.acquire(block=block, timeout=timeout)
        elif self.compute_on in [Location.THREAD]:
            if block:
                return lock.acquire(blocking=True,
                                    timeout=-1 if timeout is None else timeout)
            else:
                return lock.acquire(
                    blocking=False)  # forbidden to specify timeout
        else:
            raise Exception(
                'Cannot acquire lock in non multi process/threading environment'
            )

    # === Data Stuff =================
    def _emit_data(self, data, channel="Data", ctr=None):
        """
        Called in computation process, ie self.process
        Emits data to childs, ie child.receive_data
        """
        clock = self._ctr if ctr is None else ctr
        self.verbose(f'Emitting channel: "{channel}"', clock)
        if channel == 'Data':
            self.debug('Emitting Data of shape:', np.array(data).shape)

        for con in self.output_connections:
            if con._emitting_channel == channel:
                con._receiving_node.receive_data(
                    clock, payload={con._receiving_channel: data})

    def _process_on_proc(self):
        self.info('Started subprocess')

        self._onstart()
        self.info('Executed _onstart')

        # as long as we do not receive a termination signal, we will wait for data to be processed
        # the .empty() is not reliable (according to the python doc), but the best we have at the moment
        was_queue_empty_last_iteration = True
        was_terminated = False

        while not was_terminated or not was_queue_empty_last_iteration:
            was_terminated = was_terminated or self._acquire_lock(
                self._subprocess_info['termination_lock'], block=False)
            # block until signaled that we have new data
            # as we might receive not data after having received a termination
            #      -> we'll just poll, so that on termination we do terminate after no longer than 0.1seconds
            # self.info(was_terminated, was_queue_empty_last_iteration)
            was_queue_empty_last_iteration = True
            for queue in self._received_data.values():
                found_value, ctr = queue.update(timeout=0.00001)
                if found_value:
                    self._process(ctr)
                    was_queue_empty_last_iteration = False

        self.info('Executing _onstop')
        self._onstop()

        self.info('Finished subprocess')

    @staticmethod
    def _channel_name_to_key(name):
        return name.replace(' ', '_').lower()

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
                res[self._channel_name_to_key(key)] = cur_value
        return res

    # Most of the time when we already receive data from the next tick of some of the inputs AND the current tick would not be processed, we are likely to want to skip the tick where data was missing
    # basically: if a frame was dropped before this node, we will also drop it and not block
    # def discard_previous_tick(self, ctr):
    #     res = bool(self._retrieve_current_data(ctr=ctr + 1))
    #     if res:
    #         self.debug('cur tick data:', self._retrieve_current_data(ctr=ctr).keys())
    #         self.debug('next tick data:', self._retrieve_current_data(ctr=ctr + 1).keys())
    #     return False

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
            self.process(**_current_data, _ctr=ctr)
            for queue in self._received_data.values():
                queue.discard_before(ctr)

            # if not keep_current_data:
            #     self.discard_before
            # if not prevent_tick:
            # else:
            #     self.debug('Prevented tick')
        else:
            self.verbose('Decided not to process', ctr, _current_data.keys())

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
            self.verbose(f'Received: "{key}" with clock {ctr}')
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

    # === Connection Discovery Stuff =================
    @staticmethod
    def remove_discovered_duplicates(nodes):
        return list(set(nodes))

    @staticmethod
    def discover_childs(node):
        if len(node.output_connections) > 0:
            childs = [
                con._receiving_node.discover_childs(con._receiving_node)
                for con in node.output_connections
            ]
            return [node] + list(np.concatenate(childs))
        return [node]

    @staticmethod
    def discover_parents(node):
        if len(node.input_connections) > 0:
            parents = [
                con._emitting_node.discover_parents(con._emitting_node)
                for con in node.input_connections
            ]
            return [node] + list(np.concatenate(parents))
        return [node]

    # TODO: this will not find the parent of it's own child (same applies to discover_parents and discover_children)
    @staticmethod
    def discover_full(node):
        return node.remove_discovered_duplicates(
            node.discover_parents(node) + node.discover_childs(node))

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

        graph_attr = {"size": "10,10!", "ratio": "fill"}
        if transparent_bg: graph_attr["bgcolor"] = "#00000000"
        dot = Digraph(format='png', strict=False, graph_attr=graph_attr)

        for node in nodes:
            shape = 'rect'
            if len(node.channels_in) <= 0:
                shape = 'invtrapezium'
            if len(node.channels_out) <= 0:
                shape = 'trapezium'
            disp_name = node.name if name else str(node)
            dot.node(str(node), disp_name, shape=shape, style='rounded')

        # Second pass: add edges based on output links
        for node in nodes:
            for con in node.output_connections:
                dot.edge(str(node),
                         str(con._receiving_node),
                         label=str(con._emitting_channel))

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
        params: **channels_in
        returns bool (if process should be called with these inputs)
        """
        return set(list(map(self._channel_name_to_key,
                            self.channels_in))) <= set(list(kwargs.keys()))

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

        params: **channels_in
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


class View(Node):
    canvas = Canvas.MPL

    def __init__(self, name, compute_on=Location.PROCESS, should_time=False):
        super().__init__(name, compute_on, should_time)

        # TODO: consider if/how to disable the visualization of a node?
        # self.display = display

        # TODO: evaluate if one or two is better as maxsize (the difference should be barely noticable, but not entirely sure)
        # -> one: most up to date, but might just miss each other? probably only applicable if sensor sampling rate is vastly different from render fps?
        # -> two: always one frame behind, but might not jump then
        self._draw_state = mp.Queue(maxsize=2)

    def init_draw(self, *args, **kwargs):
        """
        Heart of the nodes drawing, should be a functional function
        """

        update_fn = self._init_draw(*args, **kwargs)
        artis_storage = {'returns': []}

        def update():
            nonlocal update_fn, artis_storage
            cur_state = {}

            try:
                cur_state = self._draw_state.get_nowait()
            except queue.Empty:
                pass
            # always execute the update, even if no new data is added, as a view might want to update not based on the self emited data
            # this happens for instance if the view wants to update based on user interaction (and not data)
            if self._should_draw(**cur_state):
                artis_storage['returns'] = update_fn(**cur_state)
                self.verbose('Decided to draw', cur_state.keys())
            else:
                self.debug('Decided not to draw', cur_state.keys())

            return artis_storage['returns']

        return update

    def stop(self, children=True):
        if self._running == True:  # -> seems important as the processes otherwise not always return (especially on fast machines, seems to be a race condition somewhere, not sure i've fully understood whats happening here, but seems to work so far)
            # we need to clear the draw state, as otherwise the feederqueue never returns and the whole script never returns
            while not self._draw_state.empty():
                self._draw_state.get()

            # should throw an error if anyone tries to insert anything into the queue after we emptied it
            # also should allow the queue to be garbage collected
            # seems not be important though...
            self._draw_state.close()

            # sets _running to false
            super().stop(children)

    # for now we only support matplotlib
    # TODO: should be updated later on
    def _init_draw(self, subfig):
        """
        Similar to init_draw, but specific to matplotlib animations
        Should be either or, not sure how to check that...
        """

        def update():
            pass

        return update

    def _should_draw(self, **cur_state):
        return bool(cur_state)

    def _emit_draw(self, **kwargs):
        """
        Called in computation process, ie self.process
        Emits data to draw process, ie draw_inits update fn
        """
        if not self._draw_state.full():
            self.verbose('Storing for draw:', kwargs.keys())
            self._draw_state.put(kwargs)


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

    channels_in = []  # must be empty!

    def __init__(self,
                 name,
                 block=False,
                 compute_on=Location.PROCESS,
                 should_time=False):
        super().__init__(name, compute_on, should_time)

        if not block and compute_on == Location.SAME:
            # TODO: consider how to not block this in Location.Same?
            raise ValueError('Block cannot be false if location=same')

        # TODO: also consider if this is better suited as parameter to start?
        self.block = block

        self._clock = Clock(node=self, should_time=should_time)
        self._ctr = self._clock.ctr

    def _node_settings(self):
        return dict({"block": self.block}, **super()._node_settings())

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
        self.info('Started subprocess')
        runner = self._run()
        try:
            # as long as we do not receive a termination signal and there is data, we will send data
            while not self._acquire_lock(
                    self._subprocess_info['termination_lock'],
                    block=False) and next(runner):
                self._ctr = self._clock.tick()
        except StopIteration:
            self.info('Reached end of run')
        self.info('Finished subprocess')

    def start(self, children=True):
        super().start(children)

        if self.compute_on in [Location.PROCESS, Location.THREAD
                               ] and self.block:
            self._subprocess_info['process'].join()
        elif self.compute_on in [Location.SAME]:
            # iterate until the generator that is run() returns false, ie no further data is to be processed
            try:
                runner = self._run()
                while next(runner):
                    self._ctr = self._clock.tick()
            except StopIteration:
                self.info('Reached end of run')


class BlockingSender(Sender):

    # TODO: check if the block parameter even does anything
    def __init__(self,
                 name,
                 block=False,
                 compute_on=Location.PROCESS,
                 should_time=False):
        super().__init__(name, block, compute_on, should_time)

        self._clock = Clock(node=self, should_time=should_time)
        self._ctr = self._clock.ctr

    def _onstart(self):
        pass

    def _onstop(self):
        pass

    def _emit_data(self, data, channel="Data"):
        super()._emit_data(data, channel)
        # as we are a blocking sender / a sensore everytime we emit a sample, we advance our clock
        if channel == "Data":
            self._ctr = self._clock.tick()

    def _process_on_proc(self):
        self.info('Started subprocess')
        try:
            self._onstart()
        except KeyboardInterrupt:
            self.info('Received Termination Signal')
            self._onstop()
        self.info('Finished subprocess')

    def start(self, children=True):
        super().start(children)

        if self.compute_on in [Location.PROCESS, Location.THREAD]:
            self._subprocess_info['process'].join()
        elif self.compute_on in [Location.SAME]:
            self._onstart()

    def stop(self, children=True):
        # first stop self, so that non-existing children don't receive inputs
        if self._running == True:  # the node might be child to multiple parents, but we just want to stop once
            self._running = False

            if self.compute_on in [Location.SAME, Location.THREAD]:
                self._onstop()
            elif self.compute_on in [Location.PROCESS]:
                self._subprocess_info['process'].terminate()

        # now stop children
        if children:
            for con in self.output_connections:
                con._receiving_node.stop()

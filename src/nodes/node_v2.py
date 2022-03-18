
from enum import Enum
import json
import numpy as np

class Location(Enum):
    SAME = 1
    THREAD = 2
    PROCESS = 3
    # SOCKET = 4


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


class Node ():
    # === Information Stuff =================
    channels_in = []
    channels_out = []

    category = "Default"
    description = ""

    example_init = {}


    # === Basic Stuff =================
    def __init__(self, name, compute_on=Location.SAME):

        self.name = name
        
        self.input_connections = []
        self.output_connections = []

        self.clock = None
        if len(self.channels_in) == 0:
            self.clock = (self, 0)

    def __repr__(self):
        return str(self)
        # return f"{str(self)} Settings:{json.dumps(self.__serialize())}"

    def __str__(self):
        return f"{self.name} [{self.__class__.__name__}]"


    # === Logging Stuff =================
    def __log(self, msg, level):
        pass

    def set_log_level(self, level):
        pass


    # === Subclass Validation Stuff =================
    def __init_subclass__(self):
        """
        Check if a new class instance is valid, ie if channels are correct, info is existing etc
        """
        pass


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
            "settings": self.__settings(),
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
        return json.dumps(res)
    
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
        emitting_node.__add_output(connection)
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
        # -> in case something goes wrong the connection remains intact
        cons[0]._emitting_node.__remove_output(cons[0]) 
        self.input_connections.remove(cons[0])


    def __add_output(self, connection):
        """
        Add an output to self. 
        Only ever called by another node, that wants this node as input
        """
        self.output_connections.append(connection)


    def __remove_output(self, connection):
        """
        Remove an output from self. 
        Only ever called by another node, that wants this node as input
        """
        cons = list(filter(connection.__eq__, self.output_connections))
        if len(cons) == 0:
            raise ValueError("Passed connection is not in inputs. Got", connection)
        self.output_connections.remove(connection)


    # === Start/Stop Stuff =================
    def start(self, children=True):
        pass

    def stop(self, children=True):
        pass


    # === Data Stuff =================
    def __emit_data(self):
        """
        Called in computation process, ie self.process
        Emits data to childs, ie child.receive_data
        """
        pass

    def __emit_draw(self):
        """
        Called in computation process, ie self.process
        Emits data to draw process, ie draw_inits update fn
        """
        pass

    def receive_data(self):
        pass


    # === Connection Discovery Stuff =================
    # not sure if this is needed, might be for the set() part, where equality should be based on pointer
    # def __eq__(self, __o):
    #     pass

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
    def timeit(self):
        pass

    # TODO: Look at the original timing code, ideas and plots


    # === Node Specific Stuff =================
    # (Computation, Render)
    def __settings(self):
        return {"name": self.name}

    def __should_process(self):
        """
        Given the inputs, this determines if process should be called on the new data or not
        """
        pass
    
    @classmethod
    def process():
        """
        Heart of the nodes processing, should be a functional processing function
        """
        pass

    @classmethod
    def init_draw(self):
        """
        Heart of the nodes drawing, should be a functional function
        """
        def update():
            pass

        return update

    def init_draw_mpl(self):
        """
        Similar to init_draw, but specific to matplotlib animations
        Should be either or, not sure how to check that...
        """
        pass



class Transform(Node):
    """
    The default node.
    Takes input and produces output
    """
    pass


class Sender(Node):
    """
    Loops the process function indefenitely
    TODO: find better name!
    """
    pass
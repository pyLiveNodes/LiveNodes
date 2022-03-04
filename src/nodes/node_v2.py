
from enum import Enum
from functools import partial
from multiprocessing.sharedctypes import Value


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
        pass

    def __str__(self):
        pass

    def __eq__(self):
        pass # TODO: needed?

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
    def copy(self, deep=False):
        pass

    def to_json(self):
        pass

    def from_json(self):
        pass

    def save(self):
        pass

    def load(self):
        pass


    # === Connection Stuff =================
    def connect_inputs_to(self, emitting_node):
        """
        Add all matching channels from the emitting nodes to self as input.
        Main function to connect two nodes together with add_input.
        """

        channels_in_common = set(self.channels_in + emitting_node.channels_out)
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
        

        # Create connection instance
        connection = Connection(emitting_node, self, emitting_channel=emitting_channel, receiving_channel=receiving_channel)
        # Find existing connections of these nodes and channels
        counter = len(filter(connection._similar, self.input_connections))
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
        cons[0].emitting_node.__remove_output(cons[0]) 
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
    def start(self, deep=True):
        pass

    def stop(self, deep=True):
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
    def discover_childs(self, deep=True):
        pass

    def discover_parents(self, deep=True):
        pass

    def discover_full(self):
        pass


    # === Drawing Graph Stuff =================
    def dot_graph_childs(self):
        pass

    def dot_graph_parents(self):
        pass

    def dot_graph_full(self):
        pass
    

    # === Performance Stuff =================
    def timeit(self):
        pass

    # TODO: Look at the original timing code, ideas and plots


    # === Node Specific Stuff =================
    # (Computation, Render)
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
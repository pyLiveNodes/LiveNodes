import inspect
import numpy as np
import queue

from graphviz import Digraph
from PIL import Image
from io import BytesIO

from typing import NamedTuple

from .connection import Connection
from .port import Port

class Ports_simple(NamedTuple):
    data: Port = Port("Data")

class Connectionist():
    ports_in = Ports_simple()
    ports_out = Ports_simple()

    def __init__(self):
        self.input_connections = []
        self.output_connections = []

    def __str__(self) -> str:
        return f"<Connectionist: {self.__class__.__name__}>"

    @staticmethod
    def __check_ports(ports):
        for x in ports:
            if not isinstance(x, Port):
                raise ValueError('Ports must subclass Port. Got:', type(x))
        
        keys = [x.key for x in ports]
        # there may not be two ports with the same label (which would result in also the same key and therefore serialzation and message passing problems)
        if len(set(keys)) != len(keys):
            raise ValueError('May not have two ports with the same label')

    def __init_subclass__(cls) -> None:
        cls.__check_ports(cls.ports_in)
        cls.__check_ports(cls.ports_out)


    def connect_inputs_to(self, emit_node: 'Connectionist'):
        """
        Add all matching channels from the emitting nodes to self as input.
        Main function to connect two nodes together with add_input.
        """

        lookup_recv = dict(zip(map(str, self.ports_in), self.ports_in))
        lookup_emit = dict(zip(map(str, emit_node.ports_out), emit_node.ports_out))
        for key in lookup_recv:
            if key in lookup_emit:
                self.add_input(emit_node=emit_node,
                            emit_port=lookup_emit[key],
                            recv_port=lookup_recv[key])

    def add_input(self,
                  emit_node: 'Connectionist',
                  emit_port: Port,
                  recv_port: Port):
        """
        Add one input to self via attributes.
        Main function to connect two nodes together with connect_inputs_to
        """

        if emit_port not in emit_node.ports_out:
            raise ValueError(
                f"Emitting Channel not present on given emitting node ({str(emit_node)}). Got",
                str(emit_port), 'Available ports:', ', '.join(map(str, emit_node.ports_out)))

        if recv_port not in self.ports_in:
            raise ValueError(
                f"Receiving Channel not present on node ({str(self)}). Got",
                str(recv_port), 'Available ports:', ', '.join(map(str, self.ports_in)))

        # This is too simple, as when connecting two nodes, we really are connecting two sub-graphs, which need to be checked
        # TODO: implement this proper
        # nodes_in_graph = emit_node.discover_full(emit_node)
        # if list(map(str, nodes_in_graph)):
        #     raise ValueError("Name already in parent sub-graph. Got:", str(self))

        # Create connection instance
        connection = Connection(emit_node,
                                self,
                                emit_port=emit_port,
                                recv_port=recv_port)

        if len(list(filter(connection.__eq__, self.input_connections))) > 0:
            raise ValueError("Connection already exists.")

        # Find existing connections of these nodes and channels
        counter = len(list(filter(connection._similar,
                                  self.input_connections)))
        # Update counter
        connection._set_connection_counter(counter)

        # Not sure if this'll actually work, otherwise we should name them _add_output
        emit_node._add_output(connection)
        self.input_connections.append(connection)

    def remove_all_inputs(self):
        for con in self.input_connections:
            self.remove_input_by_connection(con)

    def remove_input(self,
                     emit_node,
                     emit_port: Port,
                     recv_port: Port,
                     connection_counter=0):
        """
        Remove an input from self via attributes
        """
        return self.remove_input_by_connection(
            Connection(emit_node,
                       self,
                       emit_port=emit_port,
                       recv_port=recv_port,
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
        cons[0]._emit_node._remove_output(cons[0])
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

    def _is_input_connected(self, recv_port: Port):
        return any([
            x._recv_port == recv_port
            for x in self.input_connections
        ])


    @staticmethod
    def remove_discovered_duplicates(nodes):
        return list(set(nodes))

    @staticmethod
    def sort_discovered_nodes(nodes):
        return list(sorted(nodes, key=lambda x: f"{len(x.discover_output_deps(x))}_{str(x)}"))

    @staticmethod
    def discover_output_deps(node):
        # TODO: consider adding a channel parameter, ie only consider dependents of this channel
        """
        Find all nodes who depend on our output
        """
        if len(node.output_connections) > 0:
            output_deps = [
                con._receiving_node.discover_output_deps(con._receiving_node)
                for con in node.output_connections
            ]
            return [node] + list(np.concatenate(output_deps))
        return [node]

    @staticmethod
    def discover_input_deps(node):
        if len(node.input_connections) > 0:
            input_deps = [
                con._emit_node.discover_input_deps(con._emit_node)
                for con in node.input_connections
            ]
            return [node] + list(np.concatenate(input_deps))
        return [node]

    @staticmethod
    def discover_neighbors(node):
        childs = [con._receiving_node for con in node.output_connections]
        parents = [con._emit_node for con in node.input_connections]
        return node.remove_discovered_duplicates([node] + childs + parents)

    @staticmethod
    def discover_graph(node):
        discovered_nodes = node.discover_neighbors(node)
        found_nodes = [node]
        stack = queue.Queue()
        for node in discovered_nodes:
            if not node in found_nodes:
                found_nodes.append(node)
                for n in node.discover_neighbors(node):
                    if not n in discovered_nodes:
                        discovered_nodes.append(n)
                        stack.put(n)

        return node.sort_discovered_nodes(node.remove_discovered_duplicates(found_nodes))

    def requires_input_of(self, node):
        # self is always a child of itself
        return node in self.discover_input_deps(self)

    def provides_input_to(self, node):
        # self is always a parent of itself
        return node in self.discover_output_deps(self)


    def dot_graph(self, nodes, name=False, transparent_bg=False):
        graph_attr = {"size": "10,10!", "ratio": "fill"}
        if transparent_bg: graph_attr["bgcolor"] = "#00000000"
        dot = Digraph(format='png', strict=False, graph_attr=graph_attr)

        for node in nodes:
            shape = 'rect'
            if len(node.ports_in) <= 0:
                shape = 'invtrapezium'
            if len(node.ports_out) <= 0:
                shape = 'trapezium'
            disp_name = node.name if name else str(node)
            dot.node(str(node), disp_name, shape=shape, style='rounded')

        # Second pass: add edges based on output links
        for node in nodes:
            for con in node.output_connections:
                dot.edge(str(node),
                         str(con._receiving_node),
                         label=str(con._emit_port))

        return Image.open(BytesIO(dot.pipe()))

    def dot_graph_full(self, **kwargs):
        return self.dot_graph(self.discover_graph(self), **kwargs)
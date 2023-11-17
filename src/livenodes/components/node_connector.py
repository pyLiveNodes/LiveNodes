import numpy as np
import queue
from enum import Enum

import re
from graphviz import Digraph
import networkx as nx
from PIL import Image
from io import BytesIO

from typing import NamedTuple
import deprecation

from .connection import Connection
from .port import Port
from .node_logger import Logger

class Attr(Enum):
    ctr_increase = 1
    circ_breaker = 2

class Ports_simple(NamedTuple):
    data: Port = Port("Data")

class Connectionist(Logger):
    ports_in = Ports_simple()
    ports_out = Ports_simple()

    attrs = []

    def __init__(self, name="Name"):
        super().__init__()

        self.input_connections = []
        self.output_connections = []

        self.name = name

        self._set_port_keys()

    def _set_port_keys(self):
        for key in self.ports_in._fields:
            getattr(self.ports_in, key).set_key(key)
            self.debug(f'[PortsIn], setting: {key}')

        for key in self.ports_out._fields:
            getattr(self.ports_out, key).set_key(key)
            self.debug(f'[PortsOut], setting: {key}')

    def string(self, name):
        return f"{name} [{self.__class__.__name__}]"

    def __str__(self):
        return self.string(self.name)

    @staticmethod
    def str_to_dict(str):
        search = re.search("(.*?) \[(.*?)\]", str)
        if search is None:
            raise ValueError(f'Could not parse {str}')
        return {'name': search.group(1), 'class': search.group(2)}


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

    def get_port_in_by_key(self, key):
        # possible_ins = [x for x in self.ports_in._asdict().values() if x.key == key]
        # if len(possible_ins) == 0:
        #     print(self.ports_in._asdict(), [x.key for x in self.ports_in._asdict().values()])
        #     raise ValueError(f'No possible input ports for key: {key} in node: {str(self)}')
        # return possible_ins[0]
        try:
            return getattr(self.ports_in, key)
        except Exception as err:
            print(self, key)
            raise err

    def get_port_out_by_key(self, key):
        # possible_outs = [x for x in self.ports_out._asdict().values() if x.key == key]
        # if len(possible_outs) == 0:
        #     print(self.ports_out._asdict(), [x.key for x in self.ports_out._asdict().values()])
        #     raise ValueError(f'No possible output ports for key: {key} in node: {str(self)}')
        # return possible_outs[0]
        try:
            return getattr(self.ports_out, key)
        except Exception as err:
            print(self, key)
            raise err

    def get_port_in_by_label(self, label):
        for port in self.ports_in:
            if port.label == label:
                return port

        raise ValueError(f'Could not find input port on {str(self)} via label: {label}')

    def get_port_out_by_label(self, label):
        for port in self.ports_out:
            if port.label == label:
                return port

        raise ValueError(f'Could not find output port on {str(self)} via label: {label}')

    @deprecation.deprecated(details="Connect Inputs will be removed due to implicit failures. If nodes are not connected but where assumed connected.")
    def connect_inputs_to(self, emit_node: 'Connectionist'):
        """
        Add all matching channels from the emitting nodes to self as input.
        Main function to connect two nodes together with add_input.
        """

        lookup_recv = dict(zip(map(str, self.ports_in), self.ports_in))
        lookup_emit = dict(zip(map(str, emit_node.ports_out), emit_node.ports_out))
        for key in lookup_recv:
            if key in lookup_emit:
                self.warn(f'Replace with: a.add_input(b, emit_port=b.{lookup_emit[key]}, recv_port=a.{lookup_recv[key]}')
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

        # === Check if ports are available
        if emit_port not in emit_node.ports_out:
            raise ValueError(
                f"Emitting Channel not present on given emitting node ({str(emit_node)}). Got",
                str(emit_port), 'Available ports:', ', '.join(map(str, emit_node.ports_out)))

        if recv_port not in self.ports_in:
            raise ValueError(
                f"Receiving Channel not present on node ({str(self)}). Got",
                str(recv_port), 'Available ports:', ', '.join(map(str, self.ports_in)))

        # === Check if class + name are unique across connected graph
        nodes_in_emit_graph = list(self.discover_graph(emit_node))
        nodes_in_recv_graph = list(self.discover_graph(self))

        # the subgraphs may already be connected -> thus remove duplicate nodes based on instance pointers (not names!)
        combined_node_list = self.remove_discovered_duplicates(nodes_in_emit_graph + nodes_in_recv_graph)
        # if we connect two subraphs, we can always expect no duplicates in each sub-graph and thus it suffices to update the recv (ie "newly added") subgraph
        for node in nodes_in_recv_graph:
            if not node.is_unique_name(node.name, node_list=combined_node_list):
                new_name = node.create_unique_name(node.name, node_list=combined_node_list)
                self.warn(f"{str(node)} not unique in new graph. Renaming Node to: {new_name}")
                node._set_attr(name=new_name)

        # === Create connection instance
        connection = Connection(emit_node,
                                self,
                                emit_port=emit_port,
                                recv_port=recv_port)

        if len(list(filter(connection.__eq__, self.input_connections))) > 0:
            raise ValueError("Connection already exists.")

        # Not sure if this'll actually work, otherwise we should name them _add_output
        emit_node._add_output(connection)
        self.input_connections.append(connection)

        # # check if there is a circular dependency and if this is safe otherwise remove the connection again
        # for circ in self.discover_circles(self.discover_graph(self)):
        #     if self in circ:
        #         attrs = np.concatenate([n.attrs for n in circ])
        #         if Attr.circ_breaker in attrs and Attr.ctr_increase in attrs:
        #             self.info(f'Found circular dependency, but should be safe. Found attributes: {attrs}')
        #             # no return here, as the connection might still be part of another unsafe circle
        #         else:
        #             self.warn(f'Found unsafe circular dependency. Found attributes: {attrs}')
        #             self.remove_input_by_connection(connection)
        #             # connection is unsafe, other safe circles do not matter, connection has to be removed
        #             return False
        # # indicate everything worked out and the connection was established 
        # return True



    def is_unique_name(self, name, node_list=None):
        if node_list is None:
            node_list = self.discover_graph(self)

        nodes_names = list(map(str, set(node_list) - set([self])))

        return not self.string(name) in nodes_names

    def create_unique_name(self, base, node_list=None):
        if self.is_unique_name(base, node_list=node_list):
            return base

        if node_list is None:
            node_list = self.discover_graph(self)

        # basically adjust base by counting then recurse until we find a good name and return that
        return self.create_unique_name(f"{base}_1", node_list=node_list)






    def remove_all_inputs(self):
        for con in self.input_connections:
            self.remove_input_by_connection(con)

    def remove_input(self,
                     emit_node,
                     emit_port: Port,
                     recv_port: Port):
        """
        Remove an input from self via attributes
        """
        return self.remove_input_by_connection(
            Connection(emit_node,
                       self,
                       emit_port=emit_port,
                       recv_port=recv_port))

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
        if type(recv_port) is str:
            self.warn('Is connected check done via str. This will be deprecated soon, please use the according port instance.')
        return any([
            (x._recv_port == recv_port or x._recv_port.label == recv_port)
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
        return node.discover_graph(node, direction='childs', sort=False)

    @staticmethod
    def discover_input_deps(node):
        return node.discover_graph(node, direction='parents', sort=False)
    
    def has_circles(self):
        return len(list(self.discover_circles(self.discover_graph(self)))) > 0
    
    def is_on_circle(self):
        for circ in self.discover_circles(self.discover_graph(self)):
            return self in circ
        return False

    @staticmethod
    def discover_circles(nodes):
        nx_graph = Connectionist.networkx_graph(nodes)
        return nx.simple_cycles(nx_graph)
    
    @staticmethod
    def discover_parents(node):
        return node.remove_discovered_duplicates([con._emit_node for con in node.input_connections])

    @staticmethod
    def discover_childs(node):
        return node.remove_discovered_duplicates([con._recv_node for con in node.output_connections])

    @staticmethod
    def discover_neighbors(node):
        childs = node.discover_childs(node)
        parents = node.discover_parents(node)
        return node.remove_discovered_duplicates([node] + childs + parents)

    @staticmethod
    def discover_graph(node, direction='both', sort=True):
        mapper = dict(
            both=node.discover_neighbors,
            parents=node.discover_parents,
            childs=node.discover_childs,
        )
        if direction not in mapper:
            raise ValueError(f'Unknown direction: {direction}. Known: {mapper.keys()}')
        
        discovered_nodes = mapper[direction](node)
        found_nodes = [node]
        stack = queue.Queue()
        for node in discovered_nodes:
            if not node in found_nodes:
                found_nodes.append(node)
                for n in mapper[direction](node):
                    if not n in discovered_nodes:
                        discovered_nodes.append(n)
                        stack.put(n)


        found = node.remove_discovered_duplicates(found_nodes)
        if not sort:
            return found
        
        # sort for stable results (i presume) as the starting node as well as the set() operation result in non-deterministic ordering
        return node.sort_discovered_nodes(found)

    def requires_input_of(self, node):
        # self is always a child of itself
        return node in self.discover_input_deps(self)

    def provides_input_to(self, node):
        # self is always a parent of itself
        return node in self.discover_output_deps(self)

    @staticmethod
    def _sanitize_node_str(node):
        # the dot renderer doesn't like :
        return str(node).replace(':', '')
    
    @staticmethod
    def networkx_graph(nodes):
        G = nx.DiGraph()
        for node in nodes:
            for con in node.output_connections:
                G.add_edge(node, con._recv_node)
        return G
    
    def dot_graph(self, nodes, name=False, transparent_bg=False, edge_labels=True, format='png', **kwargs):
        graph_attr = {"size": "10,10!", "ratio": "fill"}
        if transparent_bg: graph_attr["bgcolor"] = "#00000000"
        dot = Digraph(format=format, strict=not edge_labels, graph_attr=graph_attr)

        for node in nodes:
            shape = 'rect'
            if len(node.ports_in) <= 0:
                shape = 'invtrapezium'
            if len(node.ports_out) <= 0:
                shape = 'trapezium'
            disp_name = node.name if name else self._sanitize_node_str(node)
            dot.node(self._sanitize_node_str(node), disp_name, shape=shape, style='rounded')

        # Second pass: add edges based on output links
        for node in nodes:
            for con in node.output_connections:
                l = None
                if edge_labels:
                    l = f"{con._emit_port.label}\n->\n{con._recv_port.label}"
                dot.edge(self._sanitize_node_str(node),
                         self._sanitize_node_str(con._recv_node),
                         label=l)
        return dot

    def dot_graph_full(self, filename=None, file_type='png', **kwargs):
        if filename is None:
            print('filename will be required in future versions')
            return Image.open(BytesIO(self.dot_graph(self.discover_graph(self), format=file_type, **kwargs).pipe()))
        else:
            self.dot_graph(self.discover_graph(self), **kwargs).render(filename=filename, format=file_type, cleanup=True)


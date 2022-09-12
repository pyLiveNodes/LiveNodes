from itertools import groupby
from .node import Node
from .components.computer import resolve_computer

class Graph():

    def __init__(self, start_node) -> None:
        self.start_node = start_node
        self.nodes = Node.discover_graph(start_node)

        self.computers = []

    def start_all(self):
        locations = groupby(self.nodes, key=lambda n: n.compute_on)
        for loc, loc_nodes in locations:
            loc_nodes = list(loc_nodes)
            print(f'Resolving computer group. Location: {loc}; Nodes: {len(loc_nodes)}')
            cmp = resolve_computer(loc)(loc_nodes)
            cmp.setup()
            self.computers.append(cmp)
        
        for cmp in self.computers:
            cmp.start()

    def stop_all(self, timeout=0):
        for cmp in self.computers:
            cmp.stop(timeout=timeout)
        self.computers = []
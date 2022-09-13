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

    def join_all(self):
        for cmp in self.computers:
            cmp.join()

    def stop_all(self, stop_timeout=0.1, close_timeout=0.1):
        for cmp in self.computers:
            cmp.stop(timeout=stop_timeout)

        for cmp in self.computers:
            cmp.close(timeout=close_timeout)

        self.computers = []
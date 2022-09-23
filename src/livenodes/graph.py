from itertools import groupby
from .node import Node
from .components.computer import parse_location, Processor_threads, Processor_process

class Graph():

    def __init__(self, start_node) -> None:
        self.start_node = start_node
        self.nodes = Node.discover_graph(start_node)

        self.computers = []

    def start_all(self):
        hosts, processes, threads = list(zip(*[parse_location(n.compute_on) for n in self.nodes]))
        
        # ignore hosts for now, as we do not have an implementation for them atm
        # host_group = groupby(sorted(zip(hosts, self.nodes), key=lambda t: t[0]))
        # for host in hosts:

        process_groups = groupby(sorted(zip(processes, threads, self.nodes), key=lambda t: t[0]), key=lambda t: t[0])
        for process, process_group in process_groups:
            _, process_threads, process_nodes = list(zip(*list(process_group)))

            if not process == '':
                cmp = Processor_process(nodes=process_nodes, location=process)
                cmp.setup()
                self.computers.append(cmp)
            else:
                thread_groups = groupby(sorted(zip(process_threads, process_nodes), key=lambda t: t[0]), key=lambda t: t[0])
                for thread, thread_group in thread_groups:
                    _, thread_nodes = list(zip(*list(thread_group)))
                    cmp = Processor_threads(nodes=thread_nodes, location=thread)
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
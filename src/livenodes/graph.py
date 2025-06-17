from collections import defaultdict
from .node import Node
from .components.computer import parse_location, Processor_process
from .components.node_logger import Logger

class Graph(Logger):

    def __init__(self, start_node) -> None:
        super().__init__()
        self.start_node = start_node
        self.nodes = Node.discover_graph(start_node)

        self.computers = []

        self.info(f'Handling {len(self.nodes)} nodes.')

    def __str__(self) -> str:
        return f"Graph"

    # def get_all_settings(self):
    #     settings = {}
    #     for node in self.nodes:
    #         settings[str(node)] == node.

    def lock_all(self):
        # Lock all nodes for processing (ie no input/output or setting changes allowed from here on)
        # also resolves bridges between nodes soon to be bridges across computers
        bridges = {str(n): {'emit': defaultdict(list), 'recv': {}} for n in self.nodes}

        for node in self.nodes:
            send_bridges, recv_bridges = node.lock()

            # one node can output/emit to multiple other nodes!
            # these connections may be unique, but at this point we don't really care about where they go, just that the output differs
            for con, bridge in send_bridges:
                bridges[str(con._emit_node)]['emit'][con._emit_port.key].append(bridge)

            # currently we only have one input connection per channel on each node
            # TODO: change this if we at some point allow multiple inputs per channel per node
            for con, bridge in recv_bridges:
                bridges[str(con._recv_node)]['recv'][con._recv_port.key] = bridge

        return bridges

    def start_all(self):
        self.info('Starting all')
        hosts, processes, threads = list(zip(*[parse_location(n.compute_on) for n in self.nodes]))

        # required for asyncio to work for local nodes
        # not required for threading, as there its already implemented.
        # However, we should really consider adding a "local" computer, which handles all of the asynio stuff, so that it is consistent within thread, process and local...
        # self.loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(self.loop)

        # not sure yet if this should be called externally yet...
        # TODO: this should only be called if there are local nodes, so maybe we should clean up the computer mess we currently have and resolve that by adding a local computer and clear hierarchy? -yh
        self.info('Locking all nodes and resolving bridges')
        bridges = self.lock_all()

        # ignore hosts for now, as we do not have an implementation for them atm
        # host_group = groupby(sorted(zip(hosts, self.nodes), key=lambda t: t[0]))
        # for host in hosts:

        self.info('Resolving computers')
        self.computers = Processor_process.group_factory(
            items=zip(processes, threads, self.nodes),
            bridges=bridges
        )

        self.info('Created computers:', list(map(str, self.computers)))
        self.info('Setting up computers')
        for cmp in self.computers:
            cmp.setup()

        self.info('Starting up computers')
        for cmp in self.computers:
            cmp.start()
                
    def is_finished(self):
        # # print([(str(cmp), cmp.is_finished()) for cmp in self.computers])
        return all([cmp.is_finished() for cmp in self.computers])

    def join_all(self, timeout=None):
        self.info('Joining computers')
        if timeout is not None:
            timeout = timeout / len(self.computers)
        for cmp in self.computers:
            cmp.join(timeout)

    def stop_all(self, stop_timeout=0.1, close_timeout=0.1):
        self.info('Stopping computers')
        for cmp in self.computers:
            cmp.stop(timeout=stop_timeout)

        self.info('Closing computers')
        for cmp in self.computers:
            cmp.close(timeout=close_timeout)

        self.computers = []

    def run_in_script(self, timeout=None):
        # TODO: rething this what is the api we actually can call here. ie sine local has a different api than thread and process i'm not sure if this works anymore...
        """Run the graph as a script, blocking until all nodes are finished."""
        try:
            self.info('Starting Graph')
            self.start_all()
            self.info('Graph started, waiting for completion')
            self.join_all(timeout=timeout)
        except KeyboardInterrupt:
            self.info("KeyboardInterrupt received: stopping graph")
        except Exception as e:
            self.error(f"An error occurred: {e}")
            raise
        finally:
            self.stop_all()
            self.info('Graph finished')
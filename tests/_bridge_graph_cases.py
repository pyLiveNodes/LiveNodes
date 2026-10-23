"""Graph scenarios for bridge_process_graph_test.py, run as subprocesses (a hang must fail a test,
not block the suite). Usage: python _bridge_graph_cases.py <case>"""
import multiprocessing as mp
import sys
import time

from livenodes import Graph, Node, Producer, Port, Ports_collection


class AnyPort(Port):
    example_values = [b'x']

    @classmethod
    def check_value(cls, value):
        return True, None


class Empty(Ports_collection):
    pass


class One(Ports_collection):
    data = AnyPort()


class Two(Ports_collection):
    data = AnyPort()
    other = AnyPort()


class SlowPayload:
    def __reduce__(self):
        time.sleep(0.2)
        return bytes, (b'x' * 1_000_000,)


def _finish(g, ok):
    g.join_all(timeout=10)
    finished = g.is_finished()
    for computer in g.computers:
        if computer.worker and computer.worker.is_alive():
            computer.worker.terminate()
            computer.worker.join(2)
        if getattr(computer, 'manager', None):
            computer.manager.shutdown()
    print('RESULT', bool(ok()), finished, flush=True)


def late_receiver_with_empty_input():
    """Two required inputs; one sends an item, the other nothing. Both close before the receiver
    starts listening. The receiver must still process the item (the empty input is closed)."""
    a_done, b_done, processed = mp.Event(), mp.Event(), mp.Event()

    class Source(Producer):
        ports_out = One()

        def __init__(self, done, values, **kwargs):
            super().__init__(**kwargs)
            self.done, self.values = done, values

        def _run(self):
            for value in self.values:
                yield self.ret(data=value)

        def _onfinish(self):
            self.done.set()

    class Sink(Node):
        ports_in = Two()
        ports_out = Empty()

        def _onstart(self):
            assert a_done.wait(5) and b_done.wait(5)
            time.sleep(.05)

        def process(self, data=None, other=None, **kwargs):
            processed.set()

    a = Source(name='A', compute_on='1:1', done=a_done, values=[b'one'])
    b = Source(name='B', compute_on='1:1', done=b_done, values=[])
    c = Sink(name='C', compute_on='2:1')
    c.add_input(a, a.ports_out.data, c.ports_in.data)
    c.add_input(b, b.ports_out.data, c.ports_in.other)
    g = Graph(a)
    g.start_all()
    _finish(g, processed.is_set)


def cross_sending_processes():
    """A(P1) -> D(P2) -> C(P1) and B(P2) -> C(P1), large slow-pickling payloads: both processes send
    to each other while closing. Must not deadlock and C must receive."""
    barrier, received = mp.Barrier(2), mp.Event()

    class Source(Producer):
        ports_out = One()

        def _run(self):
            barrier.wait(timeout=5)
            yield self.ret(data=SlowPayload())

    class Relay(Node):
        ports_in = One()
        ports_out = One()

        def process(self, data, **kwargs):
            return self.ret(data=data)

    class Sink(Node):
        ports_in = Two()
        ports_out = Empty()

        def process(self, data=None, other=None, **kwargs):
            received.set()

    a = Source(name='A', compute_on='1:1')
    b = Source(name='B', compute_on='2:1')
    d = Relay(name='D', compute_on='2:1')
    c = Sink(name='C', compute_on='1:1')
    d.add_input(a, emit_port=a.ports_out.data, recv_port=d.ports_in.data)
    c.add_input(d, emit_port=d.ports_out.data, recv_port=c.ports_in.data)
    c.add_input(b, emit_port=b.ports_out.data, recv_port=c.ports_in.other)
    g = Graph(a)
    g.start_all()
    _finish(g, received.is_set)


if __name__ == '__main__':
    {'late_receiver_with_empty_input': late_receiver_with_empty_input,
     'cross_sending_processes': cross_sending_processes}[sys.argv[1]]()

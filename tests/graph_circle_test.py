import pytest
import multiprocessing as mp

from livenodes import Node, Attr, Producer, Graph, Ports_collection
from utils import Port_Ints

class Ports_none(Ports_collection): 
    pass

class Ports_simple(Ports_collection):
    data: Port_Ints = Port_Ints("Data")

class Ports_sync(Ports_collection):
    data: Port_Ints = Port_Ints("Data")
    delayed: Port_Ints = Port_Ints("Delayed")

class SimpleNode(Node):
    ports_in = Ports_simple()
    ports_out = Ports_simple()

class Data(Producer):
    ports_in = Ports_none()
    # yes, "Data" would have been fine, but wanted to quickly test the naming parts
    # TODO: consider
    ports_out = Ports_simple()

    def _run(self):
        for ctr in range(5):
            self.info(ctr)
            yield self.ret(data=ctr)

class Save(Node):
    ports_in = Ports_simple()
    ports_out = Ports_none()

    def __init__(self, name='Save', **kwargs):
        super().__init__(name, **kwargs)
        self.out = mp.SimpleQueue()

    def process(self, data, **kwargs):
        self.debug('re data', data)
        self.out.put(data)

    def get_state(self):
        res = []
        while not self.out.empty():
            res.append(self.out.get())
        return res

class CircBreakerNodeMock(Node):
    attrs = [Attr.circ_breaker, Attr.ctr_increase]
    ports_in = Ports_simple()
    ports_out = Ports_simple()

class Sum(Node):
    ports_in = Ports_sync()
    ports_out = Ports_simple()

    def _should_process(self, data=None, delayed=None):
        return data is not None and delayed is not None

    def process(self, data, delayed, **kwargs):
        return self.ret(data=data + delayed)
    
class CtrIncrease(Node):
    attrs = [Attr.ctr_increase]
    ports_in = Ports_simple()
    ports_out = Ports_simple()

    def process(self, data, _ctr):
        return self.ret(data=data), _ctr + 1

class CircBreakerNode(Node):
    attrs = [Attr.circ_breaker]
    ports_in = Ports_sync()
    ports_out = Ports_sync()

    # NOTE: this is pureley for testing, i would highly recommend passing this as a parameter or input when implemnting your own circ_breakers
    # please rather follow this design using multiple inputs: https://gitlab.csl.uni-bremen.de/livenodes/livenodes/-/issues/39#note_22610
    # using this might actually lead to timing issues, as _should_process could be checked before the first input is processed and therefore, before the fallback is reset
    fallback = 1000

    def _finish(self, task=None):
        return super()._finish(task)

    def ready(self, input_endpoints=None, output_endpoints=None):
        future = super().ready(input_endpoints, output_endpoints)
        # This seems to be correct, since it checks for closed and empty -> but it should not yet be empty!
        self._bridges_closed = self._loop.create_task(input_endpoints['data'].onclose())
        self._bridges_closed.add_done_callback(self._finish)
        return future

    def _should_process(self, data=None, delayed=None):
        return data is not None and (delayed is not None or self.fallback is not None)

    def process(self, data, delayed=None, **kwargs):
        self.ret_accu_new(data=data)

        if self.fallback is not None:
            self.ret_accu_new(delayed=self.fallback)
            self.fallback = None
        else:
            self.ret_accu_new(delayed=delayed)
        
        return self.ret_accumulated()

# Arrange
@pytest.fixture
def create_simple_graph():
    node_a = SimpleNode(name='A')
    node_b = SimpleNode(name='B')
    node_c = SimpleNode(name='C')
    node_d = SimpleNode()
    node_e = SimpleNode()

    node_c.add_input(node_a, emit_port=SimpleNode.ports_out.data, recv_port=SimpleNode.ports_in.data)
    node_c.add_input(node_b, emit_port=SimpleNode.ports_out.data, recv_port=SimpleNode.ports_in.data)

    node_d.add_input(node_c, emit_port=SimpleNode.ports_out.data, recv_port=SimpleNode.ports_in.data)
    node_e.add_input(node_c, emit_port=SimpleNode.ports_out.data, recv_port=SimpleNode.ports_in.data)

    return node_a, node_b, node_c, node_d, node_e


class TestGraphOperations():

    def test_circ_simple(self):
        a = SimpleNode()
        assert not a.is_on_circle()

        with pytest.raises(Exception):
            a.add_input(a, emit_port=a.ports_out.data, recv_port=a.ports_in.data)

    def test_circ_complex(self, create_simple_graph):
        node_a, node_b, node_c, node_d, node_e = create_simple_graph

        with pytest.raises(Exception):
            node_a.add_input(node_e, emit_port=node_e.ports_out.data, recv_port=node_a.ports_in.data)
        

    def test_circ_allowed(self, create_simple_graph):
        node_a, node_b, node_c, node_d, node_e = create_simple_graph
        breaker = CircBreakerNodeMock()

        node_a.add_input(breaker, emit_port=breaker.ports_out.data, recv_port=node_a.ports_in.data)
        breaker.add_input(node_e, emit_port=node_e.ports_out.data, recv_port=breaker.ports_in.data)
      
    def test_circ_processing(self):
        prod = Data()
        breaker = CircBreakerNode()
        incr = CtrIncrease()
        summer = Sum()
        saver = Save()

        breaker.add_input(prod, emit_port=prod.ports_out.data, recv_port=breaker.ports_in.data)
        summer.add_input(breaker, emit_port=breaker.ports_out.data, recv_port=summer.ports_in.data)
        summer.add_input(breaker, emit_port=breaker.ports_out.delayed, recv_port=summer.ports_in.delayed)
        incr.add_input(summer, emit_port=summer.ports_out.data, recv_port=incr.ports_in.data)
        breaker.add_input(incr, emit_port=incr.ports_out.data, recv_port=breaker.ports_in.delayed)
        saver.add_input(summer, emit_port=summer.ports_out.data, recv_port=saver.ports_in.data)

        g = Graph(start_node=prod)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert g.is_finished()

        # prod will emit: [0, 1, 2, 3, 4]
        # breaker will emit: [1000, x, x, x, x] with x being the last value from summer
        # summer will emit [0 + 1000, 1 + 1000, 2 + 1001, 3 + 1003, 4 + 1006]
        assert saver.get_state() == [0 + 1000, 1 + 1000, 2 + 1001, 3 + 1003, 4 + 1006]


if __name__ == "__main__":
    prod = Data()
    breaker = CircBreakerNode()
    incr = CtrIncrease()
    summer = Sum()
    saver = Save()

    breaker.add_input(prod, emit_port=prod.ports_out.data, recv_port=breaker.ports_in.data)
    summer.add_input(breaker, emit_port=breaker.ports_out.data, recv_port=summer.ports_in.data)
    summer.add_input(breaker, emit_port=breaker.ports_out.delayed, recv_port=summer.ports_in.delayed)
    incr.add_input(summer, emit_port=summer.ports_out.data, recv_port=incr.ports_in.data)
    breaker.add_input(incr, emit_port=incr.ports_out.data, recv_port=breaker.ports_in.delayed)
    saver.add_input(summer, emit_port=summer.ports_out.data, recv_port=saver.ports_in.data)

    g = Graph(start_node=prod)
    g.start_all()
    g.join_all()
    g.stop_all()

    assert g.is_finished()

    # prod will emit: [0, 1, 2, 3, 4]
    # breaker will emit: [1000, x, x, x, x] with x being the last value from summer
    # summer will emit [0 + 1000, 1 + 1000, 2 + 1001, 3 + 1003, 4 + 1006]
    state = saver.get_state()
    # print(state)
    assert state == [0 + 1000, 1 + 1000, 2 + 1001, 3 + 1003, 4 + 1006]
import time
import pytest
import multiprocessing as mp

from livenodes import Node, Producer, Graph, get_registry

from typing import NamedTuple
from .utils import Port_Ints

class Ports_none(NamedTuple): 
    pass

class Ports_simple(NamedTuple):
    alternate_data: Port_Ints = Port_Ints("Alternate Data")

class Data(Producer):
    ports_in = Ports_none()
    # yes, "Data" would have been fine, but wanted to quickly test the naming parts
    # TODO: consider
    ports_out = Ports_simple()

    def _run(self):
        for ctr in range(10):
            self.info(ctr)
            yield self.ret(alternate_data=ctr)


class Quadratic(Node):
    ports_in = Ports_simple()
    ports_out = Ports_simple()

    def process(self, alternate_data, **kwargs):
        return self.ret(alternate_data=alternate_data**2)


class Save(Node):
    ports_in = Ports_simple()
    ports_out = Ports_none()

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.out = mp.SimpleQueue()

    def process(self, alternate_data, **kwargs):
        self.debug('re data', alternate_data)
        self.out.put(alternate_data)

    def get_state(self):
        res = []
        while not self.out.empty():
            res.append(self.out.get())
        return res


# Arrange
@pytest.fixture
def create_simple_graph():
    data = Data(name="A", compute_on="")
    quadratic = Quadratic(name="B", compute_on="")
    out1 = Save(name="C", compute_on="")
    out2 = Save(name="D", compute_on="")

    out1.connect_inputs_to(data)
    quadratic.connect_inputs_to(data)
    out2.connect_inputs_to(quadratic)

    return data, quadratic, out1, out2

@pytest.fixture
def create_simple_graph_th():
    data = Data(name="A", compute_on="1")
    quadratic = Quadratic(name="B", compute_on="1")
    out1 = Save(name="C", compute_on="2")
    out2 = Save(name="D", compute_on="1")

    out1.connect_inputs_to(data)
    quadratic.connect_inputs_to(data)
    out2.connect_inputs_to(quadratic)

    return data, quadratic, out1, out2

@pytest.fixture
def create_simple_graph_mp():
    data = Data(name="A", compute_on="1:1")
    quadratic = Quadratic(name="B", compute_on="2:1")
    out1 = Save(name="C", compute_on="3:1")
    out2 = Save(name="D", compute_on="1:1")

    out1.connect_inputs_to(data)
    quadratic.connect_inputs_to(data)
    out2.connect_inputs_to(quadratic)

    return data, quadratic, out1, out2


@pytest.fixture
def create_simple_graph_mixed():
    data = Data(name="A", compute_on="1:2")
    quadratic = Quadratic(name="B", compute_on="2:1")
    out1 = Save(name="C", compute_on="1:1")
    out2 = Save(name="D", compute_on="1")

    out1.connect_inputs_to(data)
    quadratic.connect_inputs_to(data)
    out2.connect_inputs_to(quadratic)

    return data, quadratic, out1, out2


class TestProcessing():

    def test_calc(self, create_simple_graph):
        data, quadratic, out1, out2 = create_simple_graph

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()

    def test_calc_twice(self, create_simple_graph):
        data, quadratic, out1, out2 = create_simple_graph

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()

    def test_calc_twice(self, create_simple_graph):
        data, quadratic, out1, out2 = create_simple_graph

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()

    def test_calc_th(self, create_simple_graph_th):
        data, quadratic, out1, out2 = create_simple_graph_th

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()

    def test_calc_mp(self, create_simple_graph_mp):
        data, quadratic, out1, out2 = create_simple_graph_mp

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()

    def test_calc_mixed(self, create_simple_graph_mixed):
        data, quadratic, out1, out2 = create_simple_graph_mixed

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()
        # g.stop_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()

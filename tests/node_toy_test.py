import time
import pytest
import multiprocessing as mp

from livenodes.node import Node
from livenodes.producer import Producer
from livenodes.graph import Graph

from typing import NamedTuple
from .utils import Port_Data

class Ports_none(NamedTuple): 
    pass

class Ports_simple(NamedTuple):
    data: Port_Data = Port_Data("Alternate Data")

class Data(Producer):
    ports_in = Ports_none()
    # yes, "Data" would have been fine, but wanted to quickly test the naming parts
    # TODO: consider
    ports_out = Ports_simple()

    def _run(self):
        for ctr in range(10):
            self.info(ctr)
            self._emit_data(ctr)
            yield ctr < 9


class Quadratic(Node):
    ports_in = Ports_simple()
    ports_out = Ports_simple()

    def process(self, alternate_data, **kwargs):
        self._emit_data(alternate_data**2)


class Save(Node):
    ports_in = Ports_simple()
    ports_out = Ports_none()

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.out = mp.SimpleQueue()

    def process(self, alternate_data, **kwargs):
        self.error('re data', alternate_data)
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
def create_simple_graph_mp():
    data = Data(name="A", compute_on="1:1")
    quadratic = Quadratic(name="B", compute_on="1:1")
    out1 = Save(name="C", compute_on="1:1")
    out2 = Save(name="D", compute_on="1:1")

    out1.connect_inputs_to(data)
    quadratic.connect_inputs_to(data)
    out2.connect_inputs_to(quadratic)

    return data, quadratic, out1, out2


@pytest.fixture
def create_simple_graph_mixed():
    data = Data(name="A", compute_on="1")
    quadratic = Quadratic(name="B", compute_on="")
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

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))

    def test_calc_twice(self, create_simple_graph):
        data, quadratic, out1, out2 = create_simple_graph

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))

    def test_calc_twice(self, create_simple_graph):
        data, quadratic, out1, out2 = create_simple_graph

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))


    def test_calc_mp(self, create_simple_graph_mp):
        data, quadratic, out1, out2 = create_simple_graph_mp

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))

    def test_calc_mixed(self, create_simple_graph_mixed):
        data, quadratic, out1, out2 = create_simple_graph_mixed

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))

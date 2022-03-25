import pytest
from src.nodes.node import Node, Location, Sender
import json
import time
import multiprocessing as mp

class Data(Sender):
    channels_in = []
    # yes, "Data" would have been fine, but wanted to quickly test the naming parts
    # TODO: consider
    channels_out = ["Alternate Data"]

    def _run(self):
        for i in range(10):
            self._log(i)
            self._emit_data(i, channel="Alternate Data")
            yield True
        return False


class Quadratic(Node):
    channels_in = ["Alternate Data"]
    channels_out = ["Alternate Data"]

    def process(self, alternate_data):
        self._emit_data(alternate_data ** 2, channel="Alternate Data")


class Save(Node):
    channels_in = ["Alternate Data"]
    channels_out = []

    def __init__(self, name, compute_on=Location.SAME, should_time=False):
        super().__init__(name, compute_on, should_time)
        self.out = mp.SimpleQueue()

    def process(self, alternate_data):
        self.out.put(alternate_data)

    def get_state(self):
        res = []
        while not self.out.empty():
            res.append(self.out.get())
        return res


# Arrange
@pytest.fixture
def create_simple_graph():
    data = Data(name="A")
    quadratic = Quadratic(name="B")
    out1 = Save(name="C")
    out2 = Save(name="D")
    
    out1.connect_inputs_to(data)
    quadratic.connect_inputs_to(data)
    out2.connect_inputs_to(quadratic)

    return data, quadratic, out1, out2


@pytest.fixture
def create_simple_graph_mp():
    data = Data(name="A", compute_on=Location.PROCESS)
    quadratic = Quadratic(name="B", compute_on=Location.PROCESS)
    out1 = Save(name="C", compute_on=Location.PROCESS)
    out2 = Save(name="D", compute_on=Location.PROCESS)
    
    out1.connect_inputs_to(data)
    quadratic.connect_inputs_to(data)
    out2.connect_inputs_to(quadratic)

    return data, quadratic, out1, out2

@pytest.fixture
def create_simple_graph_mixed():
    data = Data(name="A", compute_on=Location.PROCESS)
    quadratic = Quadratic(name="B", compute_on=Location.THREAD)
    out1 = Save(name="C", compute_on=Location.SAME)
    out2 = Save(name="D", compute_on=Location.THREAD)
    
    out1.connect_inputs_to(data)
    quadratic.connect_inputs_to(data)
    out2.connect_inputs_to(quadratic)

    return data, quadratic, out1, out2


class TestProcessing():

    def test_calc(self, create_simple_graph):
        data, quadratic, out1, out2 = create_simple_graph

        data.start()
        data.stop()
        
        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))


    def test_calc_mp(self, create_simple_graph_mp):
        data, quadratic, out1, out2 = create_simple_graph_mp

        data.start()
        data.stop()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))

    def test_calc_mixed(self, create_simple_graph_mixed):
        data, quadratic, out1, out2 = create_simple_graph_mixed

        data.start()
        data.stop()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))
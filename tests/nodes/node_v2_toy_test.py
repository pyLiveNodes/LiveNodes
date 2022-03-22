import pytest
from src.nodes.node_v2 import Node, Location
import json

class Data(Node):
    channels_in = []
    channels_out = ["Data"]

    ctr = 0

    def process(self):
        self._emit_data(self.ctr)
        self.ctr += 1


class Quadratic(Node):
    channels_in = ["Data"]
    channels_out = ["Data"]

    def process(self, Data):
        self._emit_data(Data ** 2)


class Save(Node):
    channels_in = ["Data"]
    channels_out = []

    def __init__(self, name, compute_on=Location.SAME, should_time=False):
        super().__init__(name, compute_on, should_time)
        self.out = []

    def process(self, Data):
        self.out.append(Data)


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


class TestProcessing():

    def test_calc(self, create_simple_graph):
        data, quadratic, out1, out2 = create_simple_graph

        data.start()
        for _ in range(10):
            data.trigger_process()
        
        assert out1.out == list(range(10))
        assert out2.out == list(map(lambda x: x**2, range(10)))


    def test_calc_mp(self, create_simple_graph_mp):
        data, quadratic, out1, out2 = create_simple_graph_mp

        data.start()
        for _ in range(10):
            data.trigger_process()
        
        assert out1.out == list(range(10))
        assert out2.out == list(map(lambda x: x**2, range(10)))
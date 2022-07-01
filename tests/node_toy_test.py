import pytest
import multiprocessing as mp

from livenodes.node import Node, Location
from livenodes.sender import Sender

import numpy as np
from livenodes.port import Port, Port_Collection

class Port_Data(Port):

    example_values = [np.array([[[1]]])]

    def __init__(self, name='Data', optional=False):
        super().__init__(name, optional)

    @staticmethod
    def check_value(value):
        if not isinstance(value, np.ndarray):
            return False, "Should be numpy array;"
        elif len(value.shape) != 3:
            return False, "Shape should be of length three (Batch, Time, Channel)"
        return True, None


class Data(Sender):
    channels_in = Port_Collection()
    # yes, "Data" would have been fine, but wanted to quickly test the naming parts
    # TODO: consider
    channels_out = Port_Collection(Port_Data("Alternate Data"))

    def _run(self):
        for ctr in range(10):
            self.info(ctr)
            self._emit_data(ctr)
            yield ctr < 9


class Quadratic(Node):
    channels_in = Port_Collection(Port_Data("Alternate Data"))
    channels_out = Port_Collection(Port_Data("Alternate Data"))

    def process(self, alternate_data, **kwargs):
        self._emit_data(alternate_data**2)


class Save(Node):
    channels_in = Port_Collection(Port_Data("Alternate Data"))
    channels_out = Port_Collection()

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.out = mp.SimpleQueue()

    def process(self, alternate_data, **kwargs):
        self.out.put(alternate_data)

    def get_state(self):
        res = []
        while not self.out.empty():
            res.append(self.out.get())
        return res


# Arrange
@pytest.fixture
def create_simple_graph():
    data = Data(name="A", compute_on=Location.SAME, block=True)
    quadratic = Quadratic(name="B", compute_on=Location.SAME)
    out1 = Save(name="C", compute_on=Location.SAME)
    out2 = Save(name="D", compute_on=Location.SAME)

    out1.connect_inputs_to(data)
    quadratic.connect_inputs_to(data)
    out2.connect_inputs_to(quadratic)

    return data, quadratic, out1, out2


@pytest.fixture
def create_simple_graph_mp():
    data = Data(name="A", compute_on=Location.PROCESS, block=True)
    quadratic = Quadratic(name="B", compute_on=Location.PROCESS)
    out1 = Save(name="C", compute_on=Location.PROCESS)
    out2 = Save(name="D", compute_on=Location.PROCESS)

    out1.connect_inputs_to(data)
    quadratic.connect_inputs_to(data)
    out2.connect_inputs_to(quadratic)

    return data, quadratic, out1, out2


@pytest.fixture
def create_simple_graph_mixed():
    data = Data(name="A", compute_on=Location.THREAD, block=True)
    quadratic = Quadratic(name="B", compute_on=Location.THREAD)
    out1 = Save(name="C", compute_on=Location.THREAD)
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

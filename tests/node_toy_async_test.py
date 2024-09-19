import time
import pytest
import multiprocessing as mp

from livenodes import Node, Ports_collection, Graph, Producer_async
import asyncio

from .utils import Port_Ints

class Ports_none(Ports_collection): 
    pass

class Ports_simple(Ports_collection):
    alternate_data: Port_Ints = Port_Ints("Alternate Data")

class Data(Producer_async):
    ports_in = Ports_none()
    # yes, "Data" would have been fine, but wanted to quickly test the naming parts
    # TODO: consider
    ports_out = Ports_simple()

    async def _async_run(self):
        for ctr in range(10):
            self.info(ctr)
            yield self.ret(alternate_data=ctr)
            await asyncio.sleep(0)

class Data_failing(Producer_async):
    ports_in = Ports_none()
    ports_out = Ports_simple()

    async def _async_run(self):
        for ctr in range(10):
            self.info(ctr)
            yield self.ret(alternate_data=ctr)
            await asyncio.sleep(0)
            if ctr == 5:
                raise ValueError('Test error')


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

    out1.add_input(data, emit_port=data.ports_out.alternate_data, recv_port=out1.ports_in.alternate_data)
    quadratic.add_input(data, emit_port=data.ports_out.alternate_data, recv_port=quadratic.ports_in.alternate_data)
    out2.add_input(quadratic, emit_port=quadratic.ports_out.alternate_data, recv_port=out2.ports_in.alternate_data)

    return data, quadratic, out1, out2

@pytest.fixture
def create_simple_graph_fail():
    data = Data_failing(name="A", compute_on="")
    quadratic = Quadratic(name="B", compute_on="")
    out1 = Save(name="C", compute_on="")
    out2 = Save(name="D", compute_on="")

    out1.add_input(data, emit_port=data.ports_out.alternate_data, recv_port=out1.ports_in.alternate_data)
    quadratic.add_input(data, emit_port=data.ports_out.alternate_data, recv_port=quadratic.ports_in.alternate_data)
    out2.add_input(quadratic, emit_port=quadratic.ports_out.alternate_data, recv_port=out2.ports_in.alternate_data)

    return data, quadratic, out1, out2

@pytest.fixture
def create_simple_graph_th():
    data = Data(name="A", compute_on="1")
    quadratic = Quadratic(name="B", compute_on="1")
    out1 = Save(name="C", compute_on="2")
    out2 = Save(name="D", compute_on="1")

    out1.add_input(data, emit_port=data.ports_out.alternate_data, recv_port=out1.ports_in.alternate_data)
    quadratic.add_input(data, emit_port=data.ports_out.alternate_data, recv_port=quadratic.ports_in.alternate_data)
    out2.add_input(quadratic, emit_port=quadratic.ports_out.alternate_data, recv_port=out2.ports_in.alternate_data)

    return data, quadratic, out1, out2

@pytest.fixture
def create_simple_graph_mp():
    data = Data(name="A", compute_on="1:1")
    quadratic = Quadratic(name="B", compute_on="2:1")
    out1 = Save(name="C", compute_on="3:1")
    out2 = Save(name="D", compute_on="1:1")

    out1.add_input(data, emit_port=data.ports_out.alternate_data, recv_port=out1.ports_in.alternate_data)
    quadratic.add_input(data, emit_port=data.ports_out.alternate_data, recv_port=quadratic.ports_in.alternate_data)
    out2.add_input(quadratic, emit_port=quadratic.ports_out.alternate_data, recv_port=out2.ports_in.alternate_data)

    return data, quadratic, out1, out2


@pytest.fixture
def create_simple_graph_mixed():
    data = Data(name="A", compute_on="1:2")
    quadratic = Quadratic(name="B", compute_on="2:1")
    out1 = Save(name="C", compute_on="1:1")
    out2 = Save(name="D", compute_on="1")

    out1.add_input(data, emit_port=data.ports_out.alternate_data, recv_port=out1.ports_in.alternate_data)
    quadratic.add_input(data, emit_port=data.ports_out.alternate_data, recv_port=quadratic.ports_in.alternate_data)
    out2.add_input(quadratic, emit_port=quadratic.ports_out.alternate_data, recv_port=out2.ports_in.alternate_data)

    return data, quadratic, out1, out2


class TestProcessingAsync():

    def test_calc(self, create_simple_graph):
        data, quadratic, out1, out2 = create_simple_graph

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert out1.get_state() == list(range(10))
        assert out2.get_state() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()

    def test_calc_fail(self, create_simple_graph_fail):
        data, quadratic, out1, out2 = create_simple_graph_fail

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert out1.get_state() == list(range(6))
        assert out2.get_state() == list(map(lambda x: x**2, range(6)))
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

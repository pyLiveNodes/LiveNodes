import pytest
from livenodes import Graph
from tests.utils import Data, Quadratic, Save

# Arrange
@pytest.fixture
def create_simple_graph():
    data = Data(name="A", compute_on="")
    quadratic = Quadratic(name="B", compute_on="")
    out1 = Save(name="C", compute_on="")
    out2 = Save(name="D", compute_on="")

    out1.add_input(data, emit_port=data.ports_out.data, recv_port=out1.ports_in.data)
    quadratic.add_input(data, emit_port=data.ports_out.data, recv_port=quadratic.ports_in.data)
    out2.add_input(quadratic, emit_port=quadratic.ports_out.data, recv_port=out2.ports_in.data)

    return data, quadratic, out1, out2

@pytest.fixture
def create_simple_graph_th():
    data = Data(name="A", compute_on="1")
    quadratic = Quadratic(name="B", compute_on="1")
    out1 = Save(name="C", compute_on="2")
    out2 = Save(name="D", compute_on="1")

    out1.add_input(data, emit_port=data.ports_out.data, recv_port=out1.ports_in.data)
    quadratic.add_input(data, emit_port=data.ports_out.data, recv_port=quadratic.ports_in.data)
    out2.add_input(quadratic, emit_port=quadratic.ports_out.data, recv_port=out2.ports_in.data)

    return data, quadratic, out1, out2

@pytest.fixture
def create_simple_graph_mp():
    data = Data(name="A", compute_on="1:1")
    quadratic = Quadratic(name="B", compute_on="2:1")
    out1 = Save(name="C", compute_on="3:1")
    out2 = Save(name="D", compute_on="1:1")

    out1.add_input(data, emit_port=data.ports_out.data, recv_port=out1.ports_in.data)
    quadratic.add_input(data, emit_port=data.ports_out.data, recv_port=quadratic.ports_in.data)
    out2.add_input(quadratic, emit_port=quadratic.ports_out.data, recv_port=out2.ports_in.data)

    return data, quadratic, out1, out2


@pytest.fixture
def create_simple_graph_mixed():
    data = Data(name="A", compute_on="1:2")
    quadratic = Quadratic(name="B", compute_on="2:1")
    out1 = Save(name="C", compute_on="1:1")
    out2 = Save(name="D", compute_on="1")

    out1.add_input(data, emit_port=data.ports_out.data, recv_port=out1.ports_in.data)
    quadratic.add_input(data, emit_port=data.ports_out.data, recv_port=quadratic.ports_in.data)
    out2.add_input(quadratic, emit_port=quadratic.ports_out.data, recv_port=out2.ports_in.data)

    return data, quadratic, out1, out2


class TestProcessing():

    def test_calc(self, create_simple_graph):
        data, quadratic, out1, out2 = create_simple_graph

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert out1.get_state_and_close() == list(range(10))
        assert out2.get_state_and_close() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()

    def test_calc_twice(self, create_simple_graph):
        data, quadratic, out1, out2 = create_simple_graph

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert out1.get_state_and_close() == list(range(10))
        assert out2.get_state_and_close() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()

        # run again but not with a copy. i don't want to support running the same graph twice as that would require us to rewrite all the states
        data = data.copy(graph=True)
        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert out1.get_state_and_close() == list(range(10))
        assert out2.get_state_and_close() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()


    def test_calc_th(self, create_simple_graph_th):
        data, quadratic, out1, out2 = create_simple_graph_th

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert out1.get_state_and_close() == list(range(10))
        assert out2.get_state_and_close() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()

    def test_calc_mp(self, create_simple_graph_mp):
        data, quadratic, out1, out2 = create_simple_graph_mp

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()

        assert out1.get_state_and_close() == list(range(10))
        assert out2.get_state_and_close() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()

    def test_calc_mixed(self, create_simple_graph_mixed):
        data, quadratic, out1, out2 = create_simple_graph_mixed

        g = Graph(start_node=data)
        g.start_all()
        g.join_all()
        g.stop_all()
        # g.stop_all()

        assert out1.get_state_and_close() == list(range(10))
        assert out2.get_state_and_close() == list(map(lambda x: x**2, range(10)))
        assert g.is_finished()

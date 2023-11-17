import pytest

from livenodes import Node, Attr

from typing import NamedTuple
from utils import Port_Ints

class Ports_simple(NamedTuple):
    data: Port_Ints = Port_Ints("Data")

class SimpleNode(Node):
    ports_in = Ports_simple()
    ports_out = Ports_simple()

class CircBreakerNode(Node):
    attrs = [Attr.circ_breaker, Attr.ctr_increase]
    ports_in = Ports_simple()
    ports_out = Ports_simple()

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
        breaker = CircBreakerNode()

        node_a.add_input(breaker, emit_port=breaker.ports_out.data, recv_port=node_a.ports_in.data)
        breaker.add_input(node_e, emit_port=node_e.ports_out.data, recv_port=breaker.ports_in.data)
      

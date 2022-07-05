import pytest

from livenodes.node_connector import Connectionist

from typing import NamedTuple
from .utils import Port_Data

class Ports_simple(NamedTuple):
    data: Port_Data("Data")

class SimpleNode(Connectionist):
    channels_in = Ports_simple()
    channels_out = Ports_simple()

class Ports_complex_in(NamedTuple):
    data: Port_Data("Data")
    meta: Port_Data("Meta")

class Ports_complex_out(NamedTuple):
    data: Port_Data("Data")
    meta: Port_Data("Meta")
    info: Port_Data("Info")

class ComplexNode(Connectionist):
    channels_in = Ports_complex_in()
    channels_out = Ports_complex_out()

# Arrange
@pytest.fixture
def create_simple_graph():
    node_a = SimpleNode()
    node_b = SimpleNode()
    node_c = SimpleNode()
    node_d = SimpleNode()
    node_e = SimpleNode()

    node_c.add_input(node_a, emit_port=SimpleNode.channels_out.data, recv_port=SimpleNode.channels_in.data)
    node_c.add_input(node_b, emit_port=SimpleNode.channels_out.data, recv_port=SimpleNode.channels_in.data)

    node_d.add_input(node_c, emit_port=SimpleNode.channels_out.data, recv_port=SimpleNode.channels_in.data)
    node_e.add_input(node_c, emit_port=SimpleNode.channels_out.data, recv_port=SimpleNode.channels_in.data)

    return node_a, node_b, node_c, node_d, node_e


@pytest.fixture
def create_simple_graph_complex_nodes():
    node_a = ComplexNode()
    node_b = ComplexNode()
    node_c = ComplexNode()

    node_b.connect_inputs_to(node_a)
    node_c.connect_inputs_to(node_b)

    return node_a, node_b, node_c


class TestGraphOperations():

    def test_relationships(self, create_simple_graph):
        node_a, node_b, node_c, node_d, node_e = create_simple_graph

        # direct relationships
        assert node_c.requires_input_of(node_a)
        assert node_a.provides_input_to(node_c)

        # further relationships
        assert node_d.requires_input_of(node_a)
        assert node_a.provides_input_to(node_d)

    def test_remove_connection(self, create_simple_graph_complex_nodes):
        node_a, node_b, _ = create_simple_graph_complex_nodes

        assert node_b.requires_input_of(node_a)

        # Remove the "Data" connection
        node_b.remove_input(node_a, 
                    emitting_channel=node_a.channels_out._data,
                    receiving_channel=node_b.channels_in._data)

        # They are still children, as the "Meta" connection remains
        assert node_b.requires_input_of(node_a)

        # Remove the "Meta" connection
        node_b.remove_input(node_a,
                            emitting_channel=node_a.channels_out._meta,
                            receiving_channel=node_b.channels_in._meta)

        # Now they shouldn't be related anymore
        assert not node_b.requires_input_of(node_a)
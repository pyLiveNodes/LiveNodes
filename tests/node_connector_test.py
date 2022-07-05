import pytest

from livenodes.node_connector import Connectionist

from typing import NamedTuple
from .utils import Port_Data

# from livenodes.port import Port
# import numpy as np
# class Port_Data(Port):

#     example_values = [np.array([[[1]]])]

#     @staticmethod
#     def check_value(value):
#         if not isinstance(value, np.ndarray):
#             return False, "Should be numpy array;"
#         elif len(value.shape) != 3:
#             return False, "Shape should be of length three (Batch, Time, Channel)"
#         return True, None


class Ports_simple(NamedTuple):
    data: Port_Data = Port_Data("Data")

class SimpleNode(Connectionist):
    ports_in = Ports_simple()
    ports_out = Ports_simple()

class Ports_complex_in(NamedTuple):
    data: Port_Data = Port_Data("Data")
    meta: Port_Data = Port_Data("Meta")

class Ports_complex_out(NamedTuple):
    data: Port_Data = Port_Data("Data")
    meta: Port_Data = Port_Data("Meta")
    info: Port_Data = Port_Data("Info")

class ComplexNode(Connectionist):
    ports_in = Ports_complex_in()
    ports_out = Ports_complex_out()

# Arrange
@pytest.fixture
def create_simple_graph():
    node_a = SimpleNode()
    node_b = SimpleNode()
    node_c = SimpleNode()
    node_d = SimpleNode()
    node_e = SimpleNode()

    node_c.add_input(node_a, emit_port=SimpleNode.ports_out.data, recv_port=SimpleNode.ports_in.data)
    node_c.add_input(node_b, emit_port=SimpleNode.ports_out.data, recv_port=SimpleNode.ports_in.data)

    node_d.add_input(node_c, emit_port=SimpleNode.ports_out.data, recv_port=SimpleNode.ports_in.data)
    node_e.add_input(node_c, emit_port=SimpleNode.ports_out.data, recv_port=SimpleNode.ports_in.data)

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
                    emit_port=ComplexNode.ports_out.data,
                    recv_port=ComplexNode.ports_in.data)

        # They are still children, as the "Meta" connection remains
        assert node_b.requires_input_of(node_a)

        # Remove the "Meta" connection
        node_b.remove_input(node_a,
                            emit_port=ComplexNode.ports_out.meta,
                            recv_port=ComplexNode.ports_in.meta)

        # Now they shouldn't be related anymore
        assert not node_b.requires_input_of(node_a)


# if __name__ == "__main__":
#     # TestGraphOperations().test_relationships(create_simple_graph())
#     TestGraphOperations().test_remove_connection(create_simple_graph_complex_nodes())
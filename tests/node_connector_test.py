import pytest

from livenodes.node_connector import Connectionist

class SimpleNode(Connectionist):
    channels_in = ["Data"]
    channels_out = ["Data"]

class ComplexNode(Connectionist):
    channels_in = ["Data", "Meta"]
    channels_out = ["Data", "Meta", "Info"]


# Arrange
@pytest.fixture
def create_simple_graph():
    node_a = SimpleNode()
    node_b = SimpleNode()
    node_c = SimpleNode()
    node_d = SimpleNode()
    node_e = SimpleNode()

    node_c.add_input(node_a)
    node_c.add_input(node_b)

    node_d.add_input(node_c)
    node_e.add_input(node_c)

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
        node_b.remove_input(node_a)

        # They are still children, as the "Meta" connection remains
        assert node_b.requires_input_of(node_a)

        # Remove the "Meta" connection
        node_b.remove_input(node_a,
                            emitting_channel="Meta",
                            receiving_channel="Meta")

        # Now they shouldn't be related anymore
        assert not node_b.requires_input_of(node_a)
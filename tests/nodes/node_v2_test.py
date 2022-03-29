import pytest
from src.nodes.node import Node
import json

class SimpleNode(Node):
    channels_in = ["Data"]
    channels_out = ["Data"]

class ComplexNode(Node):
    channels_in = ["Data", "Meta"]
    channels_out = ["Data", "Meta", "Info"]

# Arrange
@pytest.fixture
def create_simple_graph():
    node_a = SimpleNode(name="A")
    node_b = SimpleNode(name="B")
    node_c = SimpleNode(name="C")
    node_d = SimpleNode(name="D")
    node_e = SimpleNode(name="E")

    node_c.add_input(node_a)
    node_c.add_input(node_b)

    node_d.add_input(node_c)
    node_e.add_input(node_c)

    return node_a, node_b, node_c, node_d, node_e

@pytest.fixture
def create_simple_graph_complex_nodes():
    node_a = ComplexNode(name="A")
    node_b = ComplexNode(name="B")
    node_c = ComplexNode(name="C")

    node_b.connect_inputs_to(node_a)
    node_c.connect_inputs_to(node_b)
    
    return node_a, node_b, node_c

# TODO: these should be run for all types of nodes, no?
# -> seems to much of a hassle, but might make sense
# -> i would prefer if we could restrict subnodes in which functions they can overwrite!
class TestGraphOperations():

    def test_relationships(self, create_simple_graph):
        node_a, node_b, node_c, node_d, node_e = create_simple_graph

        # self relationships
        assert node_a.is_child_of(node_a)
        assert node_a.is_parent_of(node_a)

        # direct relationships
        assert node_c.is_child_of(node_a)
        assert node_a.is_parent_of(node_c)

        # further relationships
        assert node_d.is_child_of(node_a)
        assert node_a.is_parent_of(node_d)


    def test_remove_connection(self, create_simple_graph_complex_nodes):
        node_a, node_b, _= create_simple_graph_complex_nodes
        
        assert node_b.is_child_of(node_a)

        # Remove the "Data" connection
        node_b.remove_input(node_a)

        # They are still children, as the "Meta" connection remains
        assert node_b.is_child_of(node_a)

        # Remove the "Meta" connection
        node_b.remove_input(node_a, emitting_channel="Meta", receiving_channel="Meta")

        # Now they shouldn't be related anymore
        assert not node_b.is_child_of(node_a)
 




@pytest.fixture
def node_a():
    return SimpleNode(name="A")

class TestNodeOperations():
    def test_settings(self, node_a):
        # check direct serialization
        d = node_a.get_settings()
        assert set(d.keys()) == set(["class", "settings", "outputs", "inputs"])
        assert json.dumps(d['settings']) == json.dumps({"name": "A"})
        assert len(d['outputs']) == 0
        assert len(d['inputs']) == 0

    def test_copy(self, node_a):
        # check copy
        node_a_copy = node_a.copy()
        assert json.dumps(node_a.get_settings()) == json.dumps(node_a_copy.get_settings())

    def test_json(self, node_a):
        # check json format
        assert node_a.to_json() == json.dumps({str(node_a): node_a.get_settings()})

        assert node_a.to_json() == SimpleNode.from_json(json_str=node_a.to_json()).to_json()
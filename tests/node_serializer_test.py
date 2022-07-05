import pytest
import json

from livenodes.node import Node
from livenodes import get_registry

from typing import NamedTuple
from .utils import Port_Data


registry = get_registry()

class Ports_simple(NamedTuple):
    data: Port_Data = Port_Data("Data")

@registry.nodes.decorator
class SimpleNode(Node):
    ports_in = Ports_simple()
    ports_out = Ports_simple()


@pytest.fixture
def node_a():
    return SimpleNode(name="A")

@pytest.fixture
def create_connection():
    node_b = SimpleNode(name="A")
    node_c = SimpleNode(name="B")

    node_c.connect_inputs_to(node_b)
  
    return node_b

class TestNodeOperations():

    def test_node_settings(self, node_a):
        # check direct serialization
        d = node_a.get_settings()
        assert set(d.keys()) == set(["class", "settings", "inputs"])
        assert json.dumps(d['settings']) == json.dumps({
            "name":
            "A",
            "compute_on":
            node_a.compute_on
        })
        assert len(d['inputs']) == 0

    def test_node_copy(self, node_a):
        # check copy
        node_a_copy = node_a.copy()
        assert node_a_copy is not None
        assert json.dumps(node_a.get_settings()) == json.dumps(
            node_a_copy.get_settings())

    def test_node_json(self, node_a):
        # check json format
        assert json.dumps(node_a.to_dict()) == json.dumps(
            {str(node_a): node_a.get_settings()})

        node_a_des = SimpleNode.from_dict(node_a.to_dict())
        assert node_a_des is not None
        assert json.dumps(node_a.to_dict()) == json.dumps(node_a_des.to_dict())

    def test_graph_json(self, create_connection):
        assert json.dumps(create_connection.to_dict(graph=True)) == '{"A [SimpleNode]": {"class": "SimpleNode", "settings": {"name": "A", "compute_on": 1}, "inputs": []}, "B [SimpleNode]": {"class": "SimpleNode", "settings": {"name": "B", "compute_on": 1}, "inputs": [{"emit_node": "A [SimpleNode]", "receiving_node": "B [SimpleNode]", "emit_port": "data", "recv_port": "data", "connection_counter": 0}]}}'
        
        graph = Node.from_dict(create_connection.to_dict(graph=True))
        assert str(graph) == "A [SimpleNode]"
        assert str(graph.output_connections[0]._receiving_node) == "B [SimpleNode]"
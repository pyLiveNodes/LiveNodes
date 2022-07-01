import pytest
import json
import numpy as np

from livenodes.node import Node
from livenodes.port import Port, Port_Collection
from livenodes import get_registry

registry = get_registry()

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

@registry.nodes.decorator
class SimpleNode(Node):
    channels_in = Port_Collection(Port_Data())
    channels_out = Port_Collection(Port_Data())


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
        assert json.dumps(create_connection.to_dict(graph=True)) == '{"A [SimpleNode]": {"class": "SimpleNode", "settings": {"name": "A", "compute_on": 1}, "inputs": []}, "B [SimpleNode]": {"class": "SimpleNode", "settings": {"name": "B", "compute_on": 1}, "inputs": [{"emitting_node": "A [SimpleNode]", "receiving_node": "B [SimpleNode]", "emitting_channel": "data", "receiving_channel": "data", "connection_counter": 0}]}}'
        
        graph = Node.from_dict(create_connection.to_dict(graph=True))
        assert str(graph) == "A [SimpleNode]"
        assert str(graph.output_connections[0]._receiving_node) == "B [SimpleNode]"
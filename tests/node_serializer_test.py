import pytest
import json

from livenodes import get_registry, Ports_collection, Node
from .utils import Port_Ints


registry = get_registry()

class Ports_simple(Ports_collection):
    data: Port_Ints = Port_Ints("Data")

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

    node_c.add_input(node_b, emit_port=node_b.ports_out.data, recv_port=node_c.ports_in.data)
  
    return node_b

class TestNodeOperations():

    def test_name_convention_reserved_symbols(self):
        with pytest.raises(ValueError):
            SimpleNode(name="A -> B")

        with pytest.raises(ValueError):
            SimpleNode(name="A [B]")

        with pytest.raises(ValueError):
            SimpleNode(name="A.B")

    def test_name_convention_parsing(self):
        node_a = SimpleNode(name="A")
        assert str(node_a) == "A [SimpleNode]"
        assert SimpleNode.str_to_dict(str(node_a)) == {"name": "A", "class": "SimpleNode"}


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

    def test_node_copy_standalone(self, node_a):
        # check copy
        node_a_copy = node_a.copy()
        assert node_a_copy is not None
        assert json.dumps(node_a.get_settings()) == json.dumps(
            node_a_copy.get_settings())
    
    def test_node_copy_graph(self, create_connection):
        node_b = SimpleNode(name="A")
        node_c = SimpleNode(name="B")
        node_c.add_input(node_b, emit_port=node_b.ports_out.data, recv_port=node_c.ports_in.data)
    
        assert id(node_b.copy()) != id(node_b)
        assert id(node_c.copy()) != id(node_c)

    def test_node_json(self, node_a):
        # check json format
        assert json.dumps(node_a.to_dict()) == json.dumps(
            {str(node_a): node_a.get_settings()})

        node_a_des = SimpleNode.from_dict(node_a.to_dict())
        assert node_a_des is not None
        assert json.dumps(list(node_a.to_dict().values())) == json.dumps(list(node_a_des.to_dict().values()))

    def test_graph_json(self, create_connection):
        graph = Node.from_dict(create_connection.to_dict(graph=True))
        assert str(graph) == "A [SimpleNode]"
        assert str(graph.output_connections[0]._recv_node) == "B [SimpleNode]"

    def test_graph_compact_serialization(self, create_connection):
        dct = create_connection.to_compact_dict(graph=True)
        assert list(sorted(dct['Nodes'].keys())) == ["A [SimpleNode]", "B [SimpleNode]"]
        assert dct['Inputs'] == ["A [SimpleNode].data -> B [SimpleNode].data"]

    def test_graph_compact_serialization_node_w_inputs(self, create_connection):
        node_c = create_connection.output_connections[0]._recv_node
        dct = node_c.to_compact_dict(graph=True)
        assert list(sorted(dct['Nodes'].keys())) == ["A [SimpleNode]", "B [SimpleNode]"]
        assert dct['Inputs'] == ["A [SimpleNode].data -> B [SimpleNode].data"]

    def test_graph_compact_deserialization(self, create_connection):
        dct = create_connection.to_compact_dict(graph=True)
        print(dct)
        graph = Node.from_compact_dict(dct)
        assert str(graph) == "B [SimpleNode]"
        assert str(graph.input_connections[0]._emit_node) == "A [SimpleNode]"

    
    def test_graph_json_same_name(self):
        node_a = SimpleNode(name="A")
        node_b = SimpleNode(name="B")
        node_c = SimpleNode(name="B")

        node_b.add_input(node_a, emit_port=node_a.ports_out.data, recv_port=node_b.ports_in.data)
        node_c.add_input(node_a, emit_port=node_a.ports_out.data, recv_port=node_c.ports_in.data)
    
        graph = Node.from_dict(node_a.to_dict(graph=True))
        assert str(graph) == "A [SimpleNode]"
        assert str(graph.output_connections[0]._recv_node) == "B [SimpleNode]"

        
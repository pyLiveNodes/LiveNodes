import json

from .utils import NumpyEncoder

from . import get_registry

class Serializer():
    def copy(self, graph=False):
        """
        Copy the current node
        if deep=True copy all childs as well
        """
        # not sure if this will work, as from_dict expects a cls not self...
        return self.from_dict(self.to_dict(graph=graph))

    def _node_settings(self):
        return {"name": self.name, "compute_on": self.compute_on, **self._settings()}

    def get_settings(self):
        return { \
            "class": self.__class__.__name__,
            "settings": self._node_settings(),
            "inputs": [con.to_dict() for con in self.input_connections],
            # Assumption: we do not actually need the outputs, as they just mirror the inputs and the outputs can always be reconstructed from those
            # "outputs": [con.to_dict() for con in self.output_connections]
        }

    def to_dict(self, graph=False):
        # Assume no nodes in the graph have the same name+node_class -> should be checked in the add_inputs
        res = {hash(self): self.get_settings()}
        if graph:
            for node in self.sort_discovered_nodes(self.discover_graph(self)):
                res[hash(node)] = node.get_settings()
        return res

    @classmethod
    def from_dict(cls, items, initial_node=None):
        # TODO: implement children=True, parents=True
        # format should be as in to_dict, ie a dictionary, where the name is unique and the values is a dictionary with three values (settings, ins, outs)

        items_instc = {}
        initial = None

        reg = get_registry()

        # first pass: create nodes
        for name, itm in items.items():
            # module_name = f"livenodes.nodes.{itm['class'].lower()}"
            # if module_name in sys.modules:
            # module = importlib.reload(sys.modules[module_name])
            # tmp = (getattr(module, itm['class'])(**itm['settings']))

            items_instc[name] = reg.nodes.get(itm['class'], **itm['settings'])

            # assume that the first node without any inputs is the initial node...
            if initial_node is None and len(
                    items_instc[name].ports_in) <= 0:
                initial_node = name

        # not sure if we can remove this at some point...
        if initial_node is not None:
            initial = items_instc[initial_node]
        else:
            # just pick at random now, as there seems to be no initial node
            initial = list(items_instc.values())[0]

        # second pass: create connections
        for name, itm in items.items():
            # only add inputs, as, if we go through all nodes this automatically includes all outputs as well
            for con in itm['inputs']:
                items_instc[name].add_input(
                    emit_node = items_instc[con["emit_node"]],
                    emit_port = items_instc[con["emit_node"]].get_port_out_by_key(con['emit_port']),
                    recv_port = items_instc[name].get_port_in_by_key(con['recv_port'])
                    )

        return initial

    def save(self, path, graph=True):
        json_str = self.to_dict(graph=graph)

        # TODO: check if folder exists
        with open(path, 'w') as f:
            json.dump(json_str, f, cls=NumpyEncoder, indent=2)

    @classmethod
    def load(cls, path):
        with open(path, 'r') as f:
            json_str = json.load(f)
        return cls.from_dict(json_str)

    

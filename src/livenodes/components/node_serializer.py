import json
import yaml

from .utils.utils import NumpyEncoder
from livenodes.components.connection import Connection
from livenodes import get_registry

import logging
logger_ln = logging.getLogger('livenodes')

class Serializer():
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        
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

    def to_compact_dict(self, graph=False):
        self.warn('The compact graph format cannot be read again. This is just for human readability.')

        def compact_settings(settings):
            config = settings.get('settings', {})
            inputs = [
                str(Connection(**inp)) for inp in settings.get('inputs', [])
            ]
            return {'Config': config, 'Inputs': inputs}

        res = {str(self): compact_settings(self.get_settings())}
        if graph:
            for node in self.sort_discovered_nodes(self.discover_graph(self)):
                res[str(node)] = compact_settings(node.get_settings())

        return res


    def to_dict(self, graph=False):
        # Assume no nodes in the graph have the same name+node_class -> should be checked in the add_inputs
        res = {str(self): self.get_settings()}
        if graph:
            for node in self.sort_discovered_nodes(self.discover_graph(self)):
                res[str(node)] = node.get_settings()
        return res

    @classmethod
    def from_dict(cls, items, initial_node=None, ignore_connection_errors=False, **kwargs):
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

            items_instc[name] = reg.nodes.get(itm['class'], **itm['settings'], **kwargs)

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
                try:
                    items_instc[name].add_input(
                        emit_node = items_instc[con["emit_node"]],
                        emit_port = items_instc[con["emit_node"]].get_port_out_by_key(con['emit_port']),
                        recv_port = items_instc[name].get_port_in_by_key(con['recv_port'])
                        )
                except Exception as err:
                    if ignore_connection_errors:
                        logger_ln.exception(err)
                    else:
                        raise err
                        

        return initial

    def save(self, path, graph=True, extension='json', compact=False):
        if compact:
            graph_dict = self.to_compact_dict(graph=graph)
        else:
            graph_dict = self.to_dict(graph=graph)

        # backwards compatibility
        if path.endswith('.json'):
            path = path.replace('.json', '')

        # TODO: check if folder exists
        if extension == 'json':
            with open(f'{path}.{extension}', 'w') as f:
                json.dump(graph_dict, f, cls=NumpyEncoder, indent=2)
        elif extension == 'yml':
            with open(f'{path}.{extension}', 'w') as f:
                yaml.dump(graph_dict, f, allow_unicode=True)
        else:
            raise ValueError('Unkown Extension', extension)

    @classmethod
    def load(cls, path, **kwargs):
        with open(path, 'r') as f:
            json_str = json.load(f)
        return cls.from_dict(json_str, **kwargs)

    

import json
import yaml

from .utils.utils import NumpyEncoder
from livenodes.components.connection import Connection
from livenodes.components.node_connector import Connectionist
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
        dct = self.to_compact_dict(graph=graph)
        if not graph:
            dct['Inputs'] = []
        return self.from_compact_dict(dct)

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

    def compact_settings(self):
        config = self.get_settings().get('settings', {})
        inputs = [
            inp.serialize_compact() for inp in self.input_connections
        ]
        return config, inputs, str(self)

    def to_compact_dict(self, graph=False):
        if not graph:
            cfg, ins, name = self.compact_settings()
            nodes = {name: cfg}
            inputs = ins
        else:
            nodes = {}
            inputs = []
            # this does not include duplicates, as discover_graph removes them
            for node in self.discover_graph(self, direction='both', sort=True):
                # the main reason for the implementation here is to support the macro node in the ln_macro package
                cfg, ins, name = node.compact_settings()
                nodes[name] = cfg
                inputs.extend(ins)

        return {'Nodes': nodes, 'Inputs': inputs}


    @classmethod
    def from_compact_dict(cls, items, initial_node=None, ignore_connection_errors=False, **kwargs):
        # convert connections and names to the correct format and then pass to from_dict
        dct = {}
        for node_str, cfg in items['Nodes'].items():
            dct[node_str] = {'settings': cfg, 'inputs': [], **Connectionist.str_to_dict(node_str)}

        for inp in items['Inputs']:
            con = Connection.deserialize_compact(inp)
            dct[con['recv_node']]['inputs'].append(con)

        return cls.from_dict(dct, initial_node=initial_node, ignore_connection_errors=ignore_connection_errors, **kwargs)

    def save(self, path, graph=True, extension='yml'):
        # backwards compatibility
        if path.endswith('.json'):
            path = path.replace('.json', '')


        # TODO: check if folder exists
        if extension == 'json':
            logger_ln.warning('Saving to json is deprecated, please use yaml instead')
            with open(f'{path}.{extension}', 'w') as f:
                graph_dict = self.to_dict(graph=graph)
                json.dump(graph_dict, f, cls=NumpyEncoder, indent=2)

        elif extension == 'yml':
            with open(f'{path}.{extension}', 'w') as f:
                graph_dict = self.to_compact_dict(graph=graph)
                yaml.dump(graph_dict, f, allow_unicode=True)

        else:
            raise ValueError('Unkown Extension', extension)


    @classmethod
    def load(cls, path, **kwargs):
        if path.endswith('.json'):
            logger_ln.warning('Loading from json is deprecated, please use yaml instead')
            with open(path, 'r') as f:
                json_str = json.load(f)
            return cls.from_dict(json_str, **kwargs)

        elif path.endswith('.yml'):
            with open(path, 'r') as f:
                yaml_dict = yaml.load(f, Loader=yaml.Loader)
            return cls.from_compact_dict(yaml_dict, **kwargs)

        else:
            raise ValueError('Unkown Extension', path)



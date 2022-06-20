from functools import partial

import json
import os
import itertools

from PyQt5.QtWidgets import QSplitter, QWidget, QHBoxLayout
from livenodes.gui.components import CustomDialog

import qtpynodeeditor
from qtpynodeeditor import (NodeDataModel, NodeDataType, PortType)
from qtpynodeeditor.type_converter import TypeConverter

from .components.edit import NodeConfigureContainer, CustomDialog
from .components.utils import noop

class CustomNodeDataModel(NodeDataModel, verify=False):

    def __init__(self, style=None, parent=None):
        super().__init__(style, parent)
        self.association_to_node = None

    def set_node_association(self, pl_node):
        self.association_to_node = pl_node

    def __getstate__(self) -> dict:
        res = super().__getstate__()
        res['association_to_node'] = self.association_to_node
        return res

    def _get_port_infos(self, connection):
        # TODO: yes, the naming here is confusing, as qtpynode is the other way round that livenodes
        in_port, out_port = connection.ports
        emitting_channel = out_port.model.data_type[out_port.port_type][
            out_port.index].id
        receiving_channel = in_port.model.data_type[in_port.port_type][
            in_port.index].id

        smart_receicing_node = in_port.model.association_to_node
        smart_emitting_node = out_port.model.association_to_node

        return smart_emitting_node, smart_receicing_node, emitting_channel, receiving_channel

    def output_connection_created(self, connection):
        # HACK: this currently works because of the three passes below (ie create node, create conneciton, associate pl node)
        # TODO: fix this by checking if the connection already exists and if so ignore the call
        if self.association_to_node is not None:
            smart_emitting_node, smart_receicing_node, emitting_channel, receiving_channel = self._get_port_infos(
                connection)

            if smart_emitting_node is not None and smart_receicing_node is not None:
                # occours when a node was deleted, in which case this is not important anyway
                smart_receicing_node.add_input(
                    smart_emitting_node,
                    emitting_channel=emitting_channel,
                    receiving_channel=receiving_channel)

    def output_connection_deleted(self, connection):
        if self.association_to_node is not None:
            smart_emitting_node, smart_receicing_node, emitting_channel, receiving_channel = self._get_port_infos(
                connection)

            if smart_emitting_node is not None and smart_receicing_node is not None:
                # occours when a node was deleted, in which case this is not important anyway
                try:
                    smart_receicing_node.remove_input(
                        smart_emitting_node,
                        emitting_channel=emitting_channel,
                        receiving_channel=receiving_channel)
                except ValueError as err:
                    print(err)
                    # TODO: see nodes above on created...


def attatch_click_cb(node_graphic_ob, cb):
    prev_fn = node_graphic_ob.mousePressEvent

    def new_fn(event):
        cb(event)
        prev_fn(event)

    node_graphic_ob.mousePressEvent = new_fn
    return node_graphic_ob


class Config(QWidget):

    def __init__(self, pipeline_path, pipeline=None, node_registry=None, parent=None):
        super().__init__(parent)

        self._create_paths(pipeline_path)

        self.known_classes = {}
        self.known_streams = set()
        self.known_dtypes = {}

        self._create_known_classes(node_registry)

        ### Setup scene
        self.scene = qtpynodeeditor.FlowScene(registry=self.registry)

        self.scene.node_deleted.connect(self._remove_pl_node)
        self.scene.node_placed.connect(self._create_pl_node)
        # self.scene.connection_created.connect(lambda connection: print("Created", connection))
        # self.scene.connection_deleted.connect(lambda connection: print("Deleted", connection))

        connection_style = self.scene.style_collection.connection
        # Configure the style collection to use colors based on data types:
        connection_style.use_data_defined_colors = True

        view_nodes = qtpynodeeditor.FlowView(self.scene)

        self.view_configure = NodeConfigureContainer()
        # self.view_configure.setFixedWidth(300)
        self.view_configure.setMinimumWidth(300)


        grid = QSplitter()
        grid.addWidget(view_nodes) #, stretch=2)
        grid.addWidget(self.view_configure) #, stretch=1)

        layout = QHBoxLayout(self)
        layout.addWidget(grid)

        ### Add nodes and layout
        layout = None
        if os.path.exists(self.pipeline_gui_path):
            with open(self.pipeline_gui_path, 'r') as f:
                layout = json.load(f)
        print(self.pipeline_gui_path)
        self._add_pipeline(layout, pipeline)

        if layout is None:
            try:
                self.scene.auto_arrange('planar_layout')
            except Exception:
                try:
                    self.scene.auto_arrange('spring_layout')
                except Exception:
                    pass
        # self.scene.auto_arrange('graphviz_layout', prog='dot', scale=1)
        # self.scene.auto_arrange('graphviz_layout', scale=3)

    # def get_actions(self):
    #     return [ \
    #         dict(label="Cancel", fn=self.save, kind='back'),
    #         dict(label="Back", fn=noop, kind='back'),
    #     ]

    def _remove_pl_node(self, node):
        smart_node = node.model.association_to_node
        if smart_node is not None:
            smart_node.remove_all_inputs()

    def _create_pl_node(self, node):
        print("Added:", node)
        # TODO: make this more in line with the qtpynodeetitor style
        msg = CustomDialog(node)
        if msg.exec():
            # Successed
            try:
                pl_node = node.model.constructor(**msg.edit_dict)
                node.model.set_node_association(pl_node)
                node._graphics_obj = attatch_click_cb(
                    node._graphics_obj,
                    partial(self.view_configure.set_pl_node, pl_node))
            except Exception as err:
                # Failed
                print('Could not instantiate Node')
                print(err)
                self.scene.remove_node(node)
        else:
            # Canceled
            self.scene.remove_node(node)

    def _create_paths(self, pipeline_path):
        self.pipeline_path = pipeline_path
        self.pipeline_gui_path = pipeline_path.replace('/pipelines/', '/gui/',
                                                       1)

        gui_folder = '/'.join(self.pipeline_gui_path.split('/')[:-1])
        if not os.path.exists(gui_folder):
            os.mkdir(gui_folder)

    def _create_known_classes(self, node_registry):
        ### Setup Datastructures
        # style = StyleCollection.from_json(style_json)

        self.registry = qtpynodeeditor.DataModelRegistry()
        # TODO: figure out how to allow multiple connections to a single input!
        # Not relevant yet, but will be when there are sync nodes (ie sync 1-x sensor nodes) etc

        if node_registry is None:
            return 

        # .values() returns a generator
        nodes = list(node_registry.packages.values())

        # Collect and create Datatypes
        for node in nodes:
            for val in node.channels_in + node.channels_out:
                self.known_dtypes[val] = NodeDataType(id=val, name=val)

        # Collect and create Node-Classes
        for node in nodes:
            cls_name = getattr(node, '__name__', 'Unknown Class')

            cls = type(cls_name, (CustomNodeDataModel,), \
                { 'name': cls_name,
                'caption': cls_name,
                'caption_visible': True,
                'num_ports': {
                    PortType.input: len(node.channels_in),
                    PortType.output: len(node.channels_out)
                },
                'data_type': {
                    PortType.input: {i: self.known_dtypes[val] for i, val in enumerate(node.channels_in)},
                    PortType.output: {i: self.known_dtypes[val] for i, val in enumerate(node.channels_out)}
                }
                , 'constructor': node
                })
            self.known_streams.update(
                set(node.channels_in + node.channels_out))
            self.known_classes[cls_name] = cls
            self.registry.register_model(cls, category=getattr(node, "category", "Unknown"))

        # Create Converters
        # Allow any stream to map onto any other stream:
        # TODO: this could be used properly for type checking, on build (in the gui only) but is not furhter integrated into the node system itself
        for a, b in itertools.combinations(self.known_streams, 2):
            converter = TypeConverter(self.known_dtypes[a],
                                      self.known_dtypes[b], noop)
            self.registry.register_type_converter(self.known_dtypes[a],
                                                  self.known_dtypes[b],
                                                  converter)

            converter = TypeConverter(self.known_dtypes[b],
                                      self.known_dtypes[a], noop)
            self.registry.register_type_converter(self.known_dtypes[b],
                                                  self.known_dtypes[a],
                                                  converter)

    def _add_pipeline(self, layout, pipeline):
        ### Reformat Layout for easier use
        # also collect x and y min for repositioning
        layout_nodes = {}
        if layout is not None:
            min_x, min_y = 2**15, 2**15
            # first pass, collect mins and add to dict for quicker lookup
            for l_node in layout['nodes']:
                layout_nodes[l_node['model']['association_to_node']] = l_node
                min_x = min(min_x, l_node["position"]['x'])
                min_y = min(min_y, l_node["position"]['y'])

            min_x, min_y = min_x - 50, min_y - 50

            # second pass, update x and y
            for l_node in layout['nodes']:
                l_node["position"]['x'] = l_node["position"]['x'] - min_x
                l_node["position"]['y'] = l_node["position"]['y'] - min_y

        ### Add nodes
        if pipeline is not None:
            # only keep uniques
            p_nodes = {str(n): n for n in pipeline.discover_graph(pipeline)}

            # first pass: create all nodes
            s_nodes = {}
            # print([str(n) for n in p_nodes])
            for name, n in p_nodes.items():
                if name in layout_nodes:
                    # lets' hope the interface hasn't changed in between
                    # TODO: actually check if it has
                    s_nodes[name] = self.scene.restore_node(layout_nodes[name])
                else:
                    s_nodes[name] = self.scene.create_node(
                        self.known_classes[n.__class__.__name__])

            # second pass: create all connectins
            for name, n in p_nodes.items():
                # node_output refers to the node in which n is inputing data, ie n's output
                # for node_output, output_id, emitting_channel, receiving_channel in n.output_classes:
                for con in n.output_connections:
                    # print('=====')
                    out_idx = n.channels_out.index(con._emitting_channel)
                    in_idx = con._receiving_node.channels_in.index(
                        con._receiving_channel)
                    # print(out_idx, in_idx)
                    n_out = s_nodes[name][PortType.output][out_idx]
                    n_in = s_nodes[str(
                        con._receiving_node)][PortType.input][in_idx]
                    self.scene.create_connection(n_out, n_in)

            # third pass: connect gui nodes to pipeline nodes
            # TODO: this is kinda a hack so that we do not create connections twice (see custom model above)
            for name, n in p_nodes.items():
                s_nodes[name]._model.set_node_association(n)
                # COMMENT: ouch, this feels very wrong...
                s_nodes[name]._graphics_obj = attatch_click_cb(
                    s_nodes[name]._graphics_obj,
                    partial(self.view_configure.set_pl_node, n))

    def _find_initial_pl(self, pl_nodes):
        # initial node: assume the first node we come across, that doesn't have any inputs is our initial node
        # TODO: this will lead to problems further down
        # when we implement piplines as nodes, there might not be nodes without inputs, then we need to take any node and make sure the discover all etc work
        # maybe also consider adding a warning if there are graphs that are not connected ie and which one will be saved...
        initial_pl_nodes = [
            n for n in pl_nodes
            if len(n.channels_in) == 0 and len(n.output_connections) > 0
        ]

        # if we cannot find a node without inputs, take the first that hase outputs
        if len(initial_pl_nodes) == 0:
            initial_pl_nodes = [
                n for n in pl_nodes if len(n.output_connections) > 0
            ]

        # if this is still empty, raise an exception
        if len(initial_pl_nodes) == 0:
            # TODO: not sure how much sense this makes, then again, cannot think of a case where you would want to save such a graph, as it can only consist of unconnected nodes...
            raise Exception('No nodes with outputs in graph, cannot save')

        return initial_pl_nodes[0]

    def get_state(self):
        state = self.scene.__getstate__()
        vis_state = {'connections': state['connections'], 'nodes': []}
        pl_nodes = []
        for val in state['nodes']:
            if 'association_to_node' in val['model']:
                pl_nodes.append(val['model']['association_to_node'])
                val['model']['association_to_node'] = str(
                    val['model']['association_to_node'])
            vis_state['nodes'].append(val)

        return vis_state, self._find_initial_pl(pl_nodes)

    def save(self):
        vis_state, pipeline = self.get_state()
        print('initial node used for saving: ', str(pipeline))

        with open(self.pipeline_gui_path, 'w') as f:
            json.dump(vis_state, f, indent=2)

        # TODO: For the moment, lets assume the start node stays the same, otherwise we'll have a problem...
        pipeline.save(self.pipeline_path)
        pipeline.dot_graph_full(transparent_bg=True).save(
            self.pipeline_gui_path.replace('.json', '.png'), 'PNG')
        pipeline.dot_graph_full(transparent_bg=False).save(
            self.pipeline_path.replace('.json', '.png'), 'PNG')

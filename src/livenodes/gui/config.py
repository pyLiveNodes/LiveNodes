from functools import partial

import json
import os
import importlib

from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QDialogButtonBox, QDialog, QFormLayout, QCheckBox, QLineEdit, QVBoxLayout, QWidget, QHBoxLayout, QScrollArea, QLabel
from PyQt5.QtCore import Qt, pyqtSignal

import qtpynodeeditor
from qtpynodeeditor import (NodeDataModel, NodeDataType, PortType)
from qtpynodeeditor.type_converter import TypeConverter


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


def noop(*args, **kwargs):
    pass


# From: https://stackoverflow.com/questions/2556108/rreplace-how-to-replace-the-last-occurrence-of-an-expression-in-a-string
def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)


def update_node_attr(node, attr, type_cast, val):
    node._set_attr(**{attr: type_cast(val)})


class EditList(QWidget):
    changed = pyqtSignal(list)

    def __init__(self, in_list=[], parent=None):
        super().__init__(parent)

        self.in_list = in_list

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        for i, val in enumerate(self.in_list):
            if type(val) == int:
                q_in = QLineEdit(str(val))
                q_in.setValidator(QIntValidator())
                q_in.textChanged.connect(
                    partial(self._update_state, i, lambda x: int(x)
                            if x != '' else 0))
            elif type(val) == str:
                q_in = QLineEdit(str(val))
                q_in.textChanged.connect(partial(self._update_state, i, str))
            elif type(val) == bool:
                q_in = QCheckBox()
                q_in.setChecked(val)
                q_in.stateChanged.connect(partial(self._update_state, i, bool))
            elif type(val) == dict:
                q_in = EditDict(in_dict=val)
                q_in.changed.connect(partial(self._update_state, i, dict))
            elif type(val) == list:
                q_in = EditList(in_list=val)
                q_in.changed.connect(partial(self._update_state, i, list))
            else:
                q_in = QLineEdit(str(val))
                print("Type not implemented yet", type(val), i)

            layout.addWidget(q_in)

            # plus = QPushButton("+")
            # minus = QPushButton("-")

    def _update_state(self, key, type_cast, val):
        self.in_list[key] = type_cast(val)
        self.changed.emit(self.in_list)


# For the moment let's assume a dict can be recursive, but a list cannot
class EditDict(QWidget):
    changed = pyqtSignal(dict)

    def __init__(self, in_dict={}, parent=None):
        super().__init__(parent)

        # Store reference and never create a new dict, only update!
        # otherwise we'll need to apply changes recursively in other parts of the code base (ie set_state)
        self.in_dict = in_dict

        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        for key, val in in_dict.items():
            if type(val) == int:
                q_in = QLineEdit(str(val))
                q_in.setValidator(QIntValidator())
                q_in.textChanged.connect(
                    partial(self._update_state, key, lambda x: int(x)
                            if x != '' else 0))
            elif type(val) == str:
                q_in = QLineEdit(str(val))
                q_in.textChanged.connect(partial(self._update_state, key, str))
            elif type(val) == bool:
                q_in = QCheckBox()
                q_in.setChecked(val)
                q_in.stateChanged.connect(
                    partial(self._update_state, key, bool))
            elif type(val) == dict:
                q_in = EditDict(in_dict=val)
                q_in.changed.connect(partial(self._update_state, key, dict))
            elif type(val) == list:
                q_in = EditList(in_list=val)
                q_in.changed.connect(partial(self._update_state, key, list))
            else:
                q_in = QLineEdit(str(val))
                print("Type not implemented yet", type(val), key)

            layout.addRow(QLabel(key), q_in)

    def _update_state(self, key, type_cast, val):
        self.in_dict[key] = type_cast(val)
        self.changed.emit(self.in_dict)


class NodeParameterSetter(QWidget):

    def __init__(self, node=None, parent=None):
        super().__init__(parent)

        # let's assume we only have class instances here and no classes
        # for classes we would need a combination of info() and something else...
        if node is not None:
            self.edit = EditDict(in_dict=node._settings())
            # let's assume the edit interfaces do not overwrite any of the references
            # otherwise we would need to do a recursive set_attr here....

            # TODO: remove _set_attr in node, this is no good design
            self.edit.changed.connect(lambda attrs: node._set_attr(**attrs))
        else:
            self.edit = EditDict(in_dict={})

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.edit)


class NodeConfigureContainer(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.scroll_panel = QWidget()
        self.scroll_panel_layout = QHBoxLayout(self.scroll_panel)
        self.scroll_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidget(self.scroll_panel)

        self._title = QLabel("Click node to configure.")
        self._description = QLabel("")
        self._category = QLabel("")

        self.l1 = QVBoxLayout(self)
        self.l1.setContentsMargins(0, 0, 0, 0)
        self.l1.addWidget(self._title)
        self.l1.addWidget(self._description)
        self.l1.addWidget(self._category)
        self.l1.addWidget(self.scroll_area, stretch=1)

        self.params = NodeParameterSetter()
        self.scroll_panel_layout.addWidget(self.params)

    def set_pl_node(self, node, *args):
        self._title.setText(str(node))
        self._category.setText(node.category)

        new_params = NodeParameterSetter(node)

        self.scroll_panel_layout.replaceWidget(self.params, new_params)
        self.params.deleteLater()
        self.params = new_params


class CustomDialog(QDialog):

    def __init__(self, node):
        super().__init__()

        self.node = node

        self.setWindowTitle(f"Create Node: {node.model.name}")

        # TODO: replace with ok with save
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.edit_dict = node.model.constructor.example_init
        edit_form = EditDict(self.edit_dict)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(edit_form)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class Config(QWidget):

    def __init__(self, pipeline_path, pipeline=None, nodes=[], parent=None):
        super().__init__(parent)

        self._create_paths(pipeline_path)

        self.known_classes = {}
        self.known_streams = set()
        self.known_dtypes = {}

        self._create_known_classes(nodes)

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

        grid = QHBoxLayout(self)
        grid.addWidget(view_nodes)
        grid.addWidget(self.view_configure)

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

    def _create_known_classes(self, nodes):
        ### Setup Datastructures
        # style = StyleCollection.from_json(style_json)

        self.registry = qtpynodeeditor.DataModelRegistry()
        # TODO: figure out how to allow multiple connections to a single input!
        # Not relevant yet, but will be when there are sync nodes (ie sync 1-x sensor nodes) etc

        # Collect and create Datatypes
        for node in nodes:
            for val in node['channels_in'] + node['channels_out']:
                self.known_dtypes[val] = NodeDataType(id=val, name=val)

        # Collect and create Node-Classes
        for node in nodes:
            cls_name = node.get('class', 'Unknown Class')

            # HACK! TODO: fix this proper (same as in node.py): the convention of filename and class will likely not hold and feels very hacky!
            module = importlib.import_module(
                f"src.nodes.{node['class'].lower()}")

            cls = type(cls_name, (CustomNodeDataModel,), \
                { 'name': cls_name,
                'caption': cls_name,
                'caption_visible': True,
                'num_ports': {
                    PortType.input: len(node['channels_in']),
                    PortType.output: len(node['channels_out'])
                },
                'data_type': {
                    PortType.input: {i: self.known_dtypes[val] for i, val in enumerate(node['channels_in'])},
                    PortType.output: {i: self.known_dtypes[val] for i, val in enumerate(node['channels_out'])}
                }
                , 'constructor': getattr(module, node['class'])
                })
            self.known_streams.update(
                set(node['channels_in'] + node['channels_out']))
            self.known_classes[cls_name] = cls
            self.registry.register_model(cls,
                                         category=node.get(
                                             "category", "Unknown"))

        # Create Converters
        # Allow any stream to map onto Data:
        for stream in self.known_streams:
            converter = TypeConverter(self.known_dtypes[stream],
                                      self.known_dtypes["Data"], noop)
            self.registry.register_type_converter(self.known_dtypes[stream],
                                                  self.known_dtypes["Data"],
                                                  converter)

            converter = TypeConverter(self.known_dtypes["Data"],
                                      self.known_dtypes[stream], noop)
            self.registry.register_type_converter(self.known_dtypes["Data"],
                                                  self.known_dtypes[stream],
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
            p_nodes = {str(n): n for n in pipeline.discover_childs(pipeline)}

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

from functools import partial
import sys
import random
from PyQt5 import QtWidgets
from glob import glob

from PyQt5.QtGui import QPixmap, QIcon                                                                                                        
from PyQt5.QtWidgets import QToolButton, QFormLayout, QComboBox, QPushButton, QVBoxLayout, QWidget, QGridLayout, QHBoxLayout, QScrollArea, QLabel
from PyQt5.QtCore import Qt, QSize, pyqtSignal

import qtpynodeeditor
from qtpynodeeditor import (NodeData, NodeDataModel, NodeDataType, PortType,
                            StyleCollection, Connection)
from qtpynodeeditor.type_converter import TypeConverter



class MyDataModel(NodeDataModel):
    name = 'MyDataModel'
    caption = 'Caption'
    caption_visible = True
    num_ports = {PortType.input: 2,
                 PortType.output: 2,
                 }
    data_type = {
        PortType.input: {
            0: NodeDataType(id='MyNodeData', name='Data'),
            1: NodeDataType(id='MyAnnoation', name='Annotation')
        },
        PortType.output: {
            0: NodeDataType(id='MyNodeData', name='Data'),
            1: NodeDataType(id='MyAnnoation', name='Annotation')
        }
    }

    def embedded_widget(self):
        return None


def noop(*args, **kwargs):
  pass

class Config(QWidget):

    def __init__(self, pipeline=None, nodes=[], parent=None):
        super().__init__(parent)

        ### Setup Datastructures
        # style = StyleCollection.from_json(style_json)

        registry = qtpynodeeditor.DataModelRegistry()
        # TODO: figure out how to allow multiple connections to a single input!
        # Not relevant yet, but will be when there are sync nodes (ie sync 1-x sensor nodes) etc

        known_classes = {} 
        known_streams = set()
        known_dtypes = {}

        # Collect and create Datatypes
        for node in nodes:
          for val in node['in'] + node['out']:
            known_dtypes[val] = NodeDataType(id=val, name=val)

        # Collect and create Node-Classes
        for node in nodes:
          cls_name = node.get('class', 'Unknown Class')
          cls = type(cls_name, (NodeDataModel,), \
            { 'name': cls_name,
            'caption': cls_name,
            'caption_visible': True,
            'num_ports': {
              PortType.input: len(node['in']), 
              PortType.output: len(node['out'])
              },
            'data_type': {
              PortType.input: {i: known_dtypes[val] for i, val in enumerate(node['in'])},
              PortType.output: {i: known_dtypes[val] for i, val in enumerate(node['out'])}
              }
            })
          known_streams.update(set(node['in'] + node['out']))
          known_classes[cls_name] = cls
          registry.register_model(cls, category=node.get("category", "Unknown"))

        # Create Converters
        # Allow any stream to map onto Data:
        for stream in known_streams:
          converter = TypeConverter(known_dtypes[stream], known_dtypes["Data"], noop)
          registry.register_type_converter(known_dtypes[stream], known_dtypes["Data"], converter)

          converter = TypeConverter(known_dtypes["Data"], known_dtypes[stream], noop)
          registry.register_type_converter(known_dtypes["Data"], known_dtypes[stream], converter)


        ### Setup scene
        self.scene = qtpynodeeditor.FlowScene(registry=registry)

        connection_style = self.scene.style_collection.connection
        # Configure the style collection to use colors based on data types:
        connection_style.use_data_defined_colors = True

        view = qtpynodeeditor.FlowView(self.scene)

        grid = QHBoxLayout(self)
        grid.addWidget(view)


        ### Add nodes

        if pipeline is not None:
          # only keep uniques
          p_nodes = {str(n): n for n in pipeline.discover_childs(pipeline)}
          
          # first pass: create all nodes
          s_nodes = {}
          # print([str(n) for n in p_nodes])
          for name, n in p_nodes.items():
            s_nodes[name] = self.scene.create_node(known_classes[n.info()['class']])

          # second pass: create all connectins
          for name, n in p_nodes.items():
            # node_output refers to the node in which n is inputing data, ie n's output
            for node_output, output_id, data_stream, recv_data_stream in n.output_classes:
              # print('=====')
              # print(name, node_output, output_id, data_stream, recv_data_stream)
              # print(data_stream, n.info()['out'], node_output.info()['in'])
              out_idx = n.info()['out'].index(data_stream)
              in_idx = node_output.info()['in'].index(recv_data_stream)
              # print(out_idx, in_idx)
              n_out = s_nodes[name][PortType.output][out_idx]
              n_in = s_nodes[str(node_output)][PortType.input][in_idx]
              self.scene.create_connection(n_out, n_in)


        # TODO: this isn't perfect at all...
        # TODO: add saving of layouts and then try to match them when loading...
        self.scene.auto_arrange('planar_layout')
        # self.scene.auto_arrange('graphviz_layout', prog='dot', scale=1)
        # self.scene.auto_arrange('graphviz_layout', scale=3)

    def get_nodes(self):
      return self.scene.__getstate__()

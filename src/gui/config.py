from functools import partial
import sys
import random
from PyQt5 import QtWidgets
from glob import glob
import json
import os

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

def noop(*args, **kwargs):
  pass

# From: https://stackoverflow.com/questions/2556108/rreplace-how-to-replace-the-last-occurrence-of-an-expression-in-a-string
def rreplace(s, old, new, occurrence):
  li = s.rsplit(old, occurrence)
  return new.join(li)

class Config(QWidget):

    def __init__(self, pipeline_path, pipeline=None, nodes=[], parent=None):
        super().__init__(parent)

        self.pipeline = pipeline
        self.pipeline_path = pipeline_path
        self.pipeline_gui_path = rreplace(pipeline_path, '/', '/gui/', 1)

        gui_folder = '/'.join(self.pipeline_gui_path.split('/')[:-1])
        if not os.path.exists(gui_folder):
          os.mkdir(gui_folder)

        layout = None
        if os.path.exists(self.pipeline_gui_path):
          with open(self.pipeline_gui_path, 'r') as f: 
            layout = json.load(f)

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
          cls = type(cls_name, (CustomNodeDataModel,), \
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


        ### Reformat Layout for easier use
        # also collect x and y min for repositioning
        layout_nodes = {}
        if layout is not None:
          min_x, min_y = 0, 0
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

        if self.pipeline is not None:
          # only keep uniques
          p_nodes = {str(n): n for n in self.pipeline.discover_childs(self.pipeline)}
          
          # first pass: create all nodes
          s_nodes = {}
          # print([str(n) for n in p_nodes])
          for name, n in p_nodes.items():
            s_nodes[name] = self.scene.create_node(known_classes[n.info()['class']])
            s_nodes[name]._model.set_node_association(n)
            if name in layout_nodes:
              s_nodes[name].__setstate__(layout_nodes[name])

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
        if layout is None:
          self.scene.auto_arrange('planar_layout')
        # else: 
        #   self.scene.auto_arrange('rescale_layout_dict')

        # self.scene.auto_arrange('graphviz_layout', prog='dot', scale=1)
        # self.scene.auto_arrange('graphviz_layout', scale=3)

    def get_state(self):
      state = self.scene.__getstate__()
      vis_state = {"connections": state["connections"]}
      vis_state["nodes"] = []
      for val in state['nodes']:
        if "association_to_node" in val['model']:
          val['model']["association_to_node"] = str(val['model']["association_to_node"])
        vis_state['nodes'].append(val)
      
      return vis_state, self.pipeline

    def save(self):
      vis_state, pipeline = self.get_state()
      
      with open(self.pipeline_gui_path, 'w') as f: 
        json.dump(vis_state, f, indent=2) 

      pipeline.save(self.pipeline_path)

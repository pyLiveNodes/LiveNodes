from functools import partial
import sys
import random
from PyQt6 import QtWidgets
from glob import glob

from PyQt6.QtGui import QPixmap, QIcon                                                                                                        
from PyQt6.QtWidgets import QToolButton, QFormLayout, QComboBox, QPushButton, QVBoxLayout, QWidget, QGridLayout, QHBoxLayout, QScrollArea, QLabel
from PyQt6.QtCore import Qt, QSize, pyqtSignal

import qtpynodeeditor
from qtpynodeeditor import (NodeData, NodeDataModel, NodeDataType, PortType,
                            StyleCollection)
style_json = '''
    {
      "FlowViewStyle": {
        "BackgroundColor": [255, 255, 240],
        "FineGridColor": [245, 245, 230],
        "CoarseGridColor": [235, 235, 220]
      },
      "NodeStyle": {
        "NormalBoundaryColor": "darkgray",
        "SelectedBoundaryColor": "deepskyblue",
        "GradientColor0": "mintcream",
        "GradientColor1": "mintcream",
        "GradientColor2": "mintcream",
        "GradientColor3": "mintcream",
        "ShadowColor": [200, 200, 200],
        "FontColor": [10, 10, 10],
        "FontColorFaded": [100, 100, 100],
        "ConnectionPointColor": "white",
        "PenWidth": 2.0,
        "HoveredPenWidth": 2.5,
        "ConnectionPointDiameter": 10.0,
        "Opacity": 1.0
      },
      "ConnectionStyle": {
        "ConstructionColor": "gray",
        "NormalColor": "black",
        "SelectedColor": "gray",
        "SelectedHaloColor": "deepskyblue",
        "HoveredColor": "deepskyblue",
        "LineWidth": 3.0,
        "ConstructionLineWidth": 2.0,
        "PointDiameter": 10.0,
        "UseDataDefinedColors": false
      }
  }
'''


class MyNodeData(NodeData):
    data_type = NodeDataType(id='MyNodeData', name='My Node Data')


class MyDataModel(NodeDataModel):
    name = 'MyDataModel'
    caption = 'Caption'
    caption_visible = True
    num_ports = {PortType.input: 1,
                 PortType.output: 3,
                 }
    data_type = MyNodeData.data_type

    def out_data(self, port):
        print(port)


    def set_in_data(self, node_data, port):
        print(node_data, port)

    def embedded_widget(self):
        return None


class Config(QWidget):

    def __init__(self, pipeline, nodes, parent=None):
        super().__init__(parent)

        style = StyleCollection.from_json(style_json)

        registry = qtpynodeeditor.DataModelRegistry()
        registry.register_model(MyDataModel, category='My Category', style=style)
        scene = qtpynodeeditor.FlowScene(style=style, registry=registry)

        view = qtpynodeeditor.FlowView(scene)

        node = scene.create_node(MyDataModel)

        grid = QHBoxLayout(self)
        grid.addWidget(view)


# if __name__ == "__main__":
#     app = QtWidgets.QApplication([])

#     widget = Home(noop, noop)
#     widget.resize(800, 600)
#     widget.show()

#     sys.exit(app.exec())
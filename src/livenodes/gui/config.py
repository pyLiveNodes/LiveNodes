import json

from PyQt5.QtWidgets import QSplitter, QHBoxLayout

from .components.edit_node import NodeConfigureContainer
from .components.edit_graph import QT_Graph_edit
from .components.page import ActionKind, Page, Action

class Config(Page):

    def __init__(self, pipeline_path, pipeline=None, node_registry=None, parent=None):
        super().__init__(parent)

        self.edit_graph = QT_Graph_edit(pipeline_path=pipeline_path, pipeline=pipeline, node_registry=node_registry, parent=self)
        self.edit_node = NodeConfigureContainer(parent=self)
        self.edit_node.setMinimumWidth(300)

        self.edit_graph.node_selected.connect(self.edit_node.set_pl_node)

        grid = QSplitter()
        grid.addWidget(self.edit_graph)
        grid.addWidget(self.edit_node)

        self.layout = QHBoxLayout(self)
        self.layout.addWidget(grid)

    def get_actions(self):
        return [ \
            Action(label="Back", fn=self.save, kind=ActionKind.BACK),
            Action(label="Cancel", kind=ActionKind.BACK),
        ]

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

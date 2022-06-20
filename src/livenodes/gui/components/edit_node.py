from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QDialogButtonBox, QDialog, QVBoxLayout, QWidget, QHBoxLayout, QScrollArea, QLabel
from PyQt5.QtCore import Qt

from .edit import EditDict


class NodeParameterSetter(QWidget):

    def __init__(self, node=None, parent=None):
        super().__init__(parent)

        # let's assume we only have class instances here and no classes
        # for classes we would need a combination of info() and something else...
        if node is not None:
            self.edit = EditDict(in_items=node._node_settings(), extendable=False)
            # let's assume the edit interfaces do not overwrite any of the references
            # otherwise we would need to do a recursive set_attr here....

            # TODO: remove _set_attr in node, this is no good design
            self.edit.changed.connect(lambda attrs: node._set_attr(**attrs))
        else:
            self.edit = EditDict(in_items={})

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.edit, stretch=1)
        if node.__doc__ is not None:
            label = QLabel(node.__doc__)
            label.setWordWrap(True)
            self.layout.addWidget(label, stretch=0)


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
        # self.scroll_area.setHorizontalScrollBarPolicy(
        #     Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidget(self.scroll_panel)

        self._title = QLabel("Click node to configure.")
        self._category = QLabel("")

        self.l1 = QVBoxLayout(self)
        self.l1.setContentsMargins(0, 0, 0, 0)
        self.l1.addWidget(self._title)
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


class CreateNodeDialog(QDialog):

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

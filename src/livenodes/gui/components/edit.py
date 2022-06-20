from functools import partial

from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import QPushButton, QFormLayout, QCheckBox, QLineEdit, QVBoxLayout, QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import pyqtSignal

def update_node_attr(node, attr, type_cast, val):
    node._set_attr(**{attr: type_cast(val)})

def convert_str_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def convert_str_int(x):
    try:
        return int(x)
    except Exception:
        return 0
    

def type_switch(update_state_fn, key, val):
    if type(val) == int:
        q_in = QLineEdit(str(val))
        q_in.setValidator(QIntValidator())
        q_in.textChanged.connect(
            partial(update_state_fn, key, convert_str_int))
    elif type(val) == float:
        q_in = QLineEdit(str(val))
        q_in.setValidator(QDoubleValidator())
        q_in.textChanged.connect(
            partial(update_state_fn, key, convert_str_float))
    elif type(val) == str:
        q_in = QLineEdit(str(val))
        q_in.textChanged.connect(partial(update_state_fn, key, str))
    elif type(val) == bool:
        q_in = QCheckBox()
        q_in.setChecked(val)
        q_in.stateChanged.connect(
            partial(update_state_fn, key, bool))
    elif type(val) == tuple:
        q_in = EditTuple(in_items=val)
        q_in.changed.connect(partial(update_state_fn, key, tuple))
    elif type(val) == dict:
        q_in = EditDict(in_items=val)
        q_in.changed.connect(partial(update_state_fn, key, dict))
    elif type(val) == list:
        q_in = EditList(in_items=val)
        q_in.changed.connect(partial(update_state_fn, key, list))
    else:
        q_in = QLineEdit(str(val))
        print("Type not implemented yet", type(val), key)
    return q_in


class EditList(QWidget):
    changed = pyqtSignal(list)

    def __init__(self, in_items=[], extendable=True, parent=None, show=True):
        super().__init__(parent)

        self.in_items = in_items
        self.extendable = extendable

        if show:
            self.layout = QVBoxLayout(self)
            self.layout.setContentsMargins(0, 0, 0, 0)
            self._add_gui_items()

    def _helper_items(self):
        return enumerate(self.in_items)

    def _add_row(self, widget, key=None):
        self.layout.addWidget(widget)

    def _add_layout(self, layout):
        self.layout.addLayout(layout)

    def _rm_gui_items(self):
        # from: https://stackoverflow.com/questions/4528347/clear-all-widgets-in-a-layout-in-pyqt
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _add_gui_items(self):
        for key, val in self._helper_items():
            q_in = type_switch(self._update_state, key=key, val=val)
            self._add_row(widget=q_in, key=key)

            if self.extendable:
                plus = QPushButton("+")
                plus.clicked.connect(partial(self._add_itm, key=key))
                minus = QPushButton("-")
                minus.clicked.connect(partial(self._rm_itm, key=key))
                l2 = QHBoxLayout()
                l2.addWidget(plus)
                l2.addWidget(minus)
                self._add_layout(l2)

    def _add_itm(self, key):
        # print('Added item', key, self.in_items[key])
        self.in_items.insert(key, self.in_items[key])
        self.changed.emit(self.in_items)
        self._rm_gui_items()
        self._add_gui_items()

    def _rm_itm(self, key):
        # print('RM item', key, self.in_items[key])
        del self.in_items[key]
        self.changed.emit(self.in_items)
        self._rm_gui_items()
        self._add_gui_items()

    def _update_state(self, key, type_cast, val):
        self.in_items[key] = type_cast(val)
        self.changed.emit(self.in_items)


class EditDict(EditList):
    changed = pyqtSignal(dict)

    def __init__(self, in_items={}, extendable=True, parent=None):
        super().__init__(in_items=in_items, extendable=extendable, parent=parent, show=False)

        self.layout = QFormLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self._add_gui_items()

    def _helper_items(self):
        return self.in_items.items()

    def _add_row(self, widget, key=None):
        self.layout.addRow(QLabel(key), widget)
    
    def _add_layout(self, layout):
        self.layout.addRow(layout)

class EditTuple(EditList):
    changed = pyqtSignal(tuple)

    def __init__(self, in_items=(), parent=None):
        super().__init__(in_items=in_items, extendable=False, parent=parent, show=False)

        self.layout = QFormLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self._add_gui_items()

    def _update_state(self, key, type_cast, val):
        tmp = list(self.in_items)
        tmp[key] = type_cast(val)
        self.in_items = tuple(tmp)
        self.changed.emit(self.in_items)


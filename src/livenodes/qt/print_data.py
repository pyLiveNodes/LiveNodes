import multiprocessing as mp
from matplotlib.widgets import TextBox, Button

from livenodes.core.viewer import View_QT
from PyQt5.QtWidgets import QLineEdit, QVBoxLayout, QFormLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy

from . import local_registry


@local_registry.register
class Print_Data(View_QT):
    channels_in = ['Data']
    channels_out = []

    category = "Debug"
    description = ""

    example_init = {
        "name": "Display Channel Data",
    }


    def process(self, data, **kwargs):
        self._emit_draw(data=data)

    def _init_draw(self, parent):

        label = QLabel("")

        layout = QFormLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addRow(label)

        def update(data=None):
            nonlocal label
            label.setText(str(data))
        return update

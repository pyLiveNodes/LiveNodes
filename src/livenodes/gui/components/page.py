from enum import IntEnum

from PyQt5.QtWidgets import QWidget
from .utils import noop


class ActionKind(IntEnum):
    BACK = 1

class Action():
    def __init__(self, label, kind, fn=noop):
        self.label = label
        self.kind = kind
        self.fn = fn


class Page(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

    def get_actions(self):
        return [ \
            Action(label="Back", fn=self.stop, kind=ActionKind.BACK),
        ]

    # def get_state(self):
    #     # first return vis state, second pipeline state
    #     # TODO: re-consider interface...
    #     return {}, {}

    def setup_ui(self):
        pass

    def stop(self):
        pass

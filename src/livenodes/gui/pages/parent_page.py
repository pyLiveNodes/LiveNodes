from functools import partial
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from livenodes.gui.components.utils import noop

from livenodes.gui.pages.page import ActionKind, Action

class Parent(QWidget):

    def __init__(self, child, name, back_fn, parent=None):
        super().__init__(parent)

        # toolbar = self.addToolBar(name)
        # toolbar.setMovable(False)
        # home = QAction("Home", self)
        # toolbar.addAction(home)

        self.back_fn = back_fn

        actions = child.get_actions()
        backs = [Action(label=act.label, kind=act.kind, fn=partial(self._back, act.fn)) for act in actions if act.kind == ActionKind.BACK]

        if len(backs) == 0:
            backs = [Action(label="Back", fn=back_fn, kind=ActionKind.BACK)]

        toolbar = QHBoxLayout()
        for back in backs:
            button = QPushButton(back.label)
            button.setSizePolicy(QSizePolicy())
            button.clicked.connect(back.fn)
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        toolbar.addWidget(QLabel(name))

        l1 = QVBoxLayout(self)
        l1.addLayout(toolbar, stretch=0)
        l1.addWidget(child, stretch=2)

        self.child = child
    
    def _back(self, fn):
        fn()
        self.back_fn()

    def stop(self):
        if hasattr(self.child, 'stop'):
            self.child.stop()
from functools import partial
import sys
import random
from PyQt5 import QtWidgets
from glob import glob

from PyQt5.QtGui import QPixmap, QIcon                                                                                                        
from PyQt5.QtWidgets import QToolButton, QFormLayout, QComboBox, QPushButton, QVBoxLayout, QWidget, QGridLayout, QHBoxLayout, QScrollArea, QLabel
from PyQt5.QtCore import Qt, QSize, pyqtSignal

class Home(QWidget):

    def __init__(self, onstart, onconfig, pipelines="./projects/test_ask/pipelines/*.json", parent=None):
        super().__init__(parent)

        # This is somewhat fucked up...
        # self.setStyleSheet("Home {background-image: url('./static/connected_human.jpg'); background-repeat: no-repeat; background-position: center;}")

        selection = Selection(onstart, onconfig, pipelines=pipelines)

        # TODO: figure out how to fucking get this to behave as i woudl like it, ie no fucking rescales to fit because thats what images should do not fucking buttons
        grid = QHBoxLayout(self)
        grid.addWidget(selection)
        # grid.addStretch(1)

        # l1.setFixedWidth(80)

# From: https://stackoverflow.com/questions/2556108/rreplace-how-to-replace-the-last-occurrence-of-an-expression-in-a-string
def rreplace(s, old, new, occurrence):
  li = s.rsplit(old, occurrence)
  return new.join(li)

class Pipline_Selection(QWidget):
    # TODO: figure out how to hold stat...

    clicked = pyqtSignal(str)

    # Adapted from: https://gist.github.com/JokerMartini/538f8262c69c2904fa8f
    def __init__(self, pipelines, parent=None):
        super().__init__(parent)

        self.scroll_panel = QWidget()
        self.scroll_panel_layout = QHBoxLayout(self.scroll_panel)
        self.scroll_panel_layout.setContentsMargins(0,0,0,0)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.setWidget(self.scroll_panel)

        # layout
        self.mainLayout = QGridLayout(self)
        self.mainLayout.setContentsMargins(0,0,0,0)
        self.mainLayout.addWidget(self.scroll_area)

        for itm in pipelines:
            icon  = QIcon(rreplace(itm, '/pipelines/', '/gui/', 1).replace('.json', '.png'))
            button = QToolButton()
            button.setText(itm.split('/')[-1].replace('.json', ''))
            button.setIcon(icon)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.clicked.connect(partial(self.__select, itm))
            button.setIconSize(QSize(200,200))
            self.scroll_panel_layout.addWidget(button)

    def __select(self, pipline_path):
        self.clicked.emit(pipline_path)


class Selection(QWidget):
    def __init__(self, onstart, onconfig, pipelines="./pipelines/*.json"):
        super().__init__()

        self.cb_onstart = onstart
        self.cb_onconfig = onconfig

        pipelines = sorted(glob(pipelines))

        # combobox1 = QComboBox()
        # print(pipelines)
        # for itm in pipelines:
        #     combobox1.addItem(itm)

        # combobox1.currentTextChanged.connect(self.text_changed)
        self.text = pipelines[0]
        
        selection = Pipline_Selection(pipelines)
        selection.clicked.connect(self.text_changed)

        start = QPushButton("Start")
        start.clicked.connect(self.onstart)

        config = QPushButton("Config")
        config.clicked.connect(self.onconfig)

        self.selected = QLabel(self.text)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.selected)
        buttons.addWidget(config)
        buttons.addWidget(start)

        self.setProperty("cssClass", "home")

        # self.pixmap = QLabel(self)
        # w, h = self.pixmap.width(), self.pixmap.height()
        # p = QPixmap('./src/gui/static/connected_human.jpg')
        # self.pixmap.setPixmap(p.scaled(w, h))

        l1 = QVBoxLayout(self)
        # l1.addWidget(self.pixmap, stretch=1)
        l1.addStretch(1) # idea from: https://zetcode.com/gui/pysidetutorial/layoutmanagement/
        l1.addWidget(selection)
        l1.addLayout(buttons)

    def onstart(self):
        self.cb_onstart(self.text)
    
    def onconfig(self):
        self.cb_onconfig(self.text)

    def text_changed(self, text):
        self.selected.setText(text)
        self.text = text

def noop(*args, **kwargs):
    print(args, kwargs)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = Home(noop, noop)
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())
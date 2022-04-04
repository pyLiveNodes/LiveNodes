from functools import partial
from math import comb
from pickletools import pyset
import sys
import random
from PyQt5 import QtWidgets
from glob import glob

from PyQt5.QtGui import QPixmap, QIcon                                                                                                        
from PyQt5.QtWidgets import QToolButton, QFormLayout, QComboBox, QComboBox, QPushButton, QVBoxLayout, QWidget, QGridLayout, QHBoxLayout, QScrollArea, QLabel
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from sklearn import pipeline

class Home(QWidget):

    def __init__(self, onstart, onconfig, projects='./projects/*', parent=None):
        super().__init__(parent)

        # This is somewhat fucked up...
        # self.setStyleSheet("Home {background-image: url('./static/connected_human.jpg'); background-repeat: no-repeat; background-position: center;}")

        self.projects = glob(projects)

        self.onstart = onstart
        self.onconfig = onconfig

        self.qt_selection = None

        # projects = Project_Selection(projects=self.projects)
        self.qt_projects = Project_Selection(self.projects)
        self.qt_projects.selection.connect(self.select_project)

        # TODO: figure out how to fucking get this to behave as i woudl like it, ie no fucking rescales to fit because thats what images should do not fucking buttons
        self.qt_grid = QVBoxLayout(self)

        self.qt_grid.addWidget(self.qt_projects)
        # grid.addStretch(1)
        # l1.setFixedWidth(80)

        self.select_project(0)

    def _on_start(self, pipeline_path):
        self.onstart(self.cur_project, pipeline_path.replace(self.cur_project, '.'))

    def _on_config(self, pipeline_path):
        self.onconfig(self.cur_project, pipeline_path.replace(self.cur_project, '.'))


    def select_project(self, project_id):
        self.cur_project = self.projects[project_id]
        pipelines = f"{self.cur_project}/pipelines/*.json"
        qt_selection = Selection(self._on_start, self._on_config, pipelines=pipelines)
        if self.qt_selection is not None:
            self.qt_grid.removeWidget(self.qt_selection)
        self.qt_grid.addWidget(qt_selection)
        self.qt_selection = qt_selection


class Project_Selection(QWidget):
    selection = pyqtSignal(int)

    def __init__(self, projects=[], parent = None):
        super().__init__(parent)

        combo = QComboBox()
        combo.addItems(projects)
        combo.currentIndexChanged.connect(self._selected)

        l2 = QHBoxLayout(self)
        # l2.addWidget(QLabel('S-MART'))
        l2.addWidget(combo)
        l2.addStretch(2)
        # for project in projects:
        #     l2.addWidget(QLabel(project))

        # l1 = QVBoxLayout(self)
        # l1.addChildLayout(l2)
        # l1.addStretch(2)
    
    def _selected(self, id):
        self.selection.emit(id)


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
            icon = QIcon(itm.replace('/pipelines/', '/gui/').replace('.json', '.png'))
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
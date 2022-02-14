from functools import partial
import sys
from turtle import back
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
# from PyQt6.QtGui import QSizePolicy

from src.gui.home import Home
from src.gui.config import Config
from src.gui.run import Run
from src.nodes.node import Node

import json


class SubView(QWidget):
    def __init__(self, child, name, back_fn, parent=None):
        super().__init__(parent)

        # toolbar = self.addToolBar(name)
        # toolbar.setMovable(False)
        # home = QAction("Home", self)
        # toolbar.addAction(home)
        
        button = QPushButton("Back")
        button.setSizePolicy(QSizePolicy())
        button.clicked.connect(back_fn)

        toolbar = QHBoxLayout() 
        toolbar.addWidget(button)
        toolbar.addStretch(1)
        toolbar.addWidget(QLabel(name))

        l1 = QVBoxLayout(self)
        l1.addLayout(toolbar)
        l1.addWidget(child)

        self.child = child
    
    def stop(self):
        if hasattr(self.child, 'stop'):
            self.child.stop()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.central_widget = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.central_widget)

        self.widget_home = Home(onconfig=self.onconfig, onstart=self.onstart)
        self.central_widget.addWidget(self.widget_home)

        # for some fucking reason i cannot figure out how to set the css class only on the home class... so hacking this by adding and removign the class on view change...
        self.central_widget.setProperty("cssClass", "home")
        # self.widget_home.setProperty("cssClass", "home")

    def return_home(self):
        cur = self.central_widget.currentWidget()
        
        # TODO: this shoudl really be in a onclose event inside of config rather than here..., but i don't know yet when/how those are called or connected to...
        if isinstance(cur.child, Config):
            print(cur.child.get_nodes())
            # for n in cur.child.get_nodes().values():
            #     print(n.__getstate__())
        
        self.central_widget.setCurrentWidget(self.widget_home)
        self.central_widget.removeWidget(cur)
        cur.stop()
        print("Nr of views: ", self.central_widget.count())

    def onstart(self, pipeline_path):
        pipeline = Node.load(pipeline_path)
        widget_run = SubView(child=Run(pipeline=pipeline), name=f"Running: {pipeline_path}", back_fn=self.return_home)
        self.central_widget.addWidget(widget_run)
        self.central_widget.setCurrentWidget(widget_run)

    def onconfig(self, pipeline_path):
        with open("nodes.json", 'r') as f:
            known_nodes = json.load(f)

        pipeline = Node.load(pipeline_path)
        widget_run = SubView(child=Config(pipeline=pipeline, nodes=known_nodes), name=f"Configuring: {pipeline_path}", back_fn=self.return_home)
        self.central_widget.addWidget(widget_run)
        self.central_widget.setCurrentWidget(widget_run)



if __name__ == '__main__':
    app = QtWidgets.QApplication([])

    with open('./src/gui/static/style.qss', 'r') as f:
        app.setStyleSheet(f.read())

    window = MainWindow()
    window.resize(1400, 820)
    window.show()
    sys.exit(app.exec())
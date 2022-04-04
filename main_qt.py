from functools import partial
import sys
from turtle import back
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
# from PyQt5.QtGui import QSizePolicy

from src.gui.home import Home
from src.gui.config import Config
from src.gui.run import Run
from src.nodes.node import Node

from nodes_collect import discover_infos

from src.nodes.utils import logger
import datetime
import time
import os


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

        self.log_file = None

        self.home_dir = os.getcwd()
        print('CWD:', os.getcwd())

        # for some fucking reason i cannot figure out how to set the css class only on the home class... so hacking this by adding and removign the class on view change...
        # self.central_widget.setProperty("cssClass", "home")
        # self.widget_home.setProperty("cssClass", "home")
    
    def stop(self):
        cur = self.central_widget.currentWidget()
        if hasattr(cur, 'stop'):
            cur.stop()
            
        if self.log_file is not None:
            logger.remove_cb(self._log_helper)
            self.log_file.close()
            self.log_file = None

    def closeEvent(self, event):
        self.stop()
        return super().closeEvent(event)

    def return_home(self):
        cur = self.central_widget.currentWidget()
        
        # TODO: this shoudl really be in a onclose event inside of config rather than here..., but i don't know yet when/how those are called or connected to...
        if isinstance(cur.child, Config):
            cur.child.save()
            # vis_state, new_pl = cur.child.get_nodes()
            # print(vis_state)
            # for n in cur.child.get_nodes().values():
            #     print(n.__getstate__())
        
        self.stop()
        self.central_widget.setCurrentWidget(self.widget_home)
        self.central_widget.removeWidget(cur)
        print("Nr of views: ", self.central_widget.count())
        os.chdir(self.home_dir)
        print('CWD:', os.getcwd())

    def _log_helper(self, msg):
        self.log_file.write(msg + '\n')
        self.log_file.flush()

    def onstart(self, project_path, pipeline_path):
        os.chdir(project_path)
        print('CWD:', os.getcwd())

        log_folder = './logs'
        log_file=f"{log_folder}/{datetime.datetime.fromtimestamp(time.time())}"
        
        if not os.path.exists(log_folder):
            os.mkdir(log_folder)

        self.log_file = open(log_file, 'a')
        logger.register_cb(self._log_helper)

        pipeline = Node.load(pipeline_path)
        # TODO: make these logs project dependent as well
        widget_run = SubView(child=Run(pipeline=pipeline), name=f"Running: {pipeline_path}", back_fn=self.return_home)
        self.central_widget.addWidget(widget_run)
        self.central_widget.setCurrentWidget(widget_run)

    def onconfig(self, project_path, pipeline_path):
        # in production we should switch this (no need to always load all modules!), but for now it's easier like this
        # with open("nodes.json", 'r') as f:
        #     known_nodes = json.load(f)
        known_nodes = discover_infos()

        os.chdir(project_path)
        print('CWD:', os.getcwd())

        pipeline = Node.load(pipeline_path)
        widget_run = SubView(child=Config(pipeline=pipeline, nodes=known_nodes, pipeline_path=pipeline_path), name=f"Configuring: {pipeline_path}", back_fn=self.return_home)
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
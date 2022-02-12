import sys
from turtle import back
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
# from PyQt6.QtGui import QSizePolicy

from src.gui.home import Home
from src.gui.run import Run
from src.nodes.node import Node


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

        self.widget_home = Home(parent=self, onconfig=self.onconfig, onstart=self.onstart)
        self.central_widget.addWidget(self.widget_home)

    def return_home(self):
        cur = self.central_widget.currentWidget()
        self.central_widget.setCurrentWidget(self.widget_home)
        self.central_widget.removeWidget(cur)
        cur.stop()
        print("Nr of views: ", self.central_widget.count())

    def onstart(self, pipeline_path):
        pipeline = Node.load(pipeline_path)
        widget_run = SubView(child=Run(pipeline=pipeline), name=f"Run: {pipeline_path}", back_fn=self.return_home)
        self.central_widget.addWidget(widget_run)
        self.central_widget.setCurrentWidget(widget_run)

    def onconfig(self, pipeline_path):
        print(pipeline_path)



if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.resize(1020, 720)
    window.show()
    sys.exit(app.exec())
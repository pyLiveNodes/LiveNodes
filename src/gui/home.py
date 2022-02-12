import sys
import random
from PyQt6 import QtWidgets
from glob import glob

# from PyQt6.QtGui import QPixmap                                                                                                          
from PyQt6.QtWidgets import QComboBox, QPushButton, QVBoxLayout, QWidget, QGridLayout, QHBoxLayout

class Home(QWidget):

    def __init__(self, onstart, onconfig, pipelines="./pipelines/*.json", parent=None):
        super().__init__(parent)

        # This is somewhat fucked up...
        # self.setStyleSheet("Home {background-image: url('./static/connected_human.jpg'); background-repeat: no-repeat; background-position: center;}")

        selection = Selection(onstart, onconfig, pipelines=pipelines)

        # TODO: figure out how to fucking get this to behave as i woudl like it, ie no fucking rescales to fit because thats what images should do not fucking buttons
        grid = QHBoxLayout(self)
        grid.addWidget(selection)
        grid.addStretch(1)

        # l1.setFixedWidth(80)



class Selection(QWidget):
    def __init__(self, onstart, onconfig, pipelines="./pipelines/*.json"):
        super().__init__()

        self.cb_onstart = onstart
        self.cb_onconfig = onconfig

        combobox1 = QComboBox()
        pipelines = sorted(glob(pipelines))
        print(pipelines)
        for itm in pipelines:
            combobox1.addItem(itm)

        combobox1.currentTextChanged.connect(self.text_changed)
        self.text = pipelines[0]
        
        start = QPushButton("Start")
        start.clicked.connect(self.onstart)

        config = QPushButton("Config")
        config.clicked.connect(self.onconfig)

        l1 = QVBoxLayout(self)
        l1.addStretch(1) # idea from: https://zetcode.com/gui/pysidetutorial/layoutmanagement/
        l1.addWidget(combobox1)
        l1.addWidget(start)
        l1.addWidget(config)
        l1.addStretch(1)

    def onstart(self):
        self.cb_onstart(self.text)
    
    def onconfig(self):
        self.cb_onconfig(self.text)

    def text_changed(self, text):
        self.text = text

def noop(*args, **kwargs):
    print(args, kwargs)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = Home(noop, noop)
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())
from src.nodes.playback import Playback

pl = Playback(files="./data/KneeBandageCSL2018/**/*.h5", sample_rate=1000)

pl.add_output(lambda data: ())

import sys
import time

import numpy as np

from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

import numpy as np
from PyQt6 import QtGui
import sys
import matplotlib as mpl
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt

from PyQt6.QtCore import QTimer, pyqtSlot  # Import new bits needed

import threading

# From: https://stackoverflow.com/questions/39835300/python-qt-and-matplotlib-scatter-plots-with-blitting
class mplWidget(FigureCanvasQTAgg):
    def __init__(self):
        super(mplWidget, self).__init__(mpl.figure.Figure(figsize=(7, 7)))

        self.setupAnim()
        self.show()

    def setupAnim(self):
        channel_names = ['Gonio2', 'GyroLow1', 'GyroLow2', 'GyroLow3']
        recorded_channels = [
            'EMG1', 'EMG2', 'EMG3', 'EMG4',
            'Airborne',
            'AccUp1', 'AccUp2', 'AccUp3',
            'Gonio1',
            'AccLow1', 'AccLow2', 'AccLow3',
            'Gonio2',
            'GyroUp1', 'GyroUp2', 'GyroUp3',
            'GyroLow1', 'GyroLow2', 'GyroLow3']
        idx = np.isin(recorded_channels, channel_names).nonzero()[0]
        
        pl.draw_raw(self.figure, idx, channel_names)
        
        self.animation = FuncAnimation(self.figure, pl.draw,
                                       interval=10, blit=True)



# From: https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html
class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)

        layout.addWidget(mplWidget())



if __name__ == "__main__":
    # Check whether there is already a running QApplication (e.g., if running
    # from an IDE).
    qapp = QtWidgets.QApplication.instance()
    if not qapp:
        qapp = QtWidgets.QApplication(sys.argv)

    pipelineThread = threading.Thread(target = pl.start_processing)
    pipelineThread.daemon = True
    pipelineThread.start()

    app = ApplicationWindow()
    app.show()
    app.activateWindow()
    app.raise_()
    qapp.exec()


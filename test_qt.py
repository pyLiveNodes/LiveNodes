from src.nodes.playback import Playback

pl = Playback(files="./data/KneeBandageCSL2018/**/*.h5", sample_rate=1000)

pl.add_output(lambda data: print(data))


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


# From: https://stackoverflow.com/questions/39835300/python-qt-and-matplotlib-scatter-plots-with-blitting
class mplWidget(FigureCanvasQTAgg):
    def __init__(self):
        super(mplWidget, self).__init__(mpl.figure.Figure(figsize=(7, 7)))

        self.setupAnim()
        self.show()

    def setupAnim(self):
        ax = self.figure.add_axes([0, 0, 1, 1], frameon=False)
        ax.axis([0, 1, 0, 1])
        ax.axis('off')

        # Create rain data
        self.n_drops = 50
        self.rain_drops = np.zeros(self.n_drops, dtype=[('position', float, 2),
                                                        ('size',     float, 1),
                                                        ('growth',   float, 1),
                                                        ('color',    float, 4)
                                                        ])

        # Initialize the raindrops in random positions and with
        # random growth rates.
        self.rain_drops['position'] = np.random.uniform(0, 1, (self.n_drops, 2))
        self.rain_drops['growth'] = np.random.uniform(50, 200, self.n_drops)

        # Construct the scatter which we will update during animation
        # as the raindrops develop.
        self.scat = ax.scatter(self.rain_drops['position'][:, 0],
                               self.rain_drops['position'][:, 1],
                               s=self.rain_drops['size'],
                               lw=0.5, facecolors='none',
                               edgecolors=self.rain_drops['color'])

        self.animation = FuncAnimation(self.figure, self.update_plot,
                                       interval=10, blit=True)

    def update_plot(self, frame_number):
        # Get an index which we can use to re-spawn the oldest raindrop.
        indx = frame_number % self.n_drops

        # Make all colors more transparent as time progresses.
        self.rain_drops['color'][:, 3] -= 1./len(self.rain_drops)
        self.rain_drops['color'][:, 3] = np.clip(self.rain_drops['color'][:, 3], 0, 1)

        # Make all circles bigger.
        self.rain_drops['size'] += self.rain_drops['growth']

        # Pick a new position for oldest rain drop, resetting its size,
        # color and growth factor.
        self.rain_drops['position'][indx] = np.random.uniform(0, 1, 2)
        self.rain_drops['size'][indx] = 5
        self.rain_drops['color'][indx] = (0, 0, 0, 1)
        self.rain_drops['growth'][indx] = np.random.uniform(50, 200)

        # Update the scatter collection, with the new colors,
        # sizes and positions.
        self.scat.set_edgecolors(self.rain_drops['color'])
        self.scat.set_sizes(self.rain_drops['size'])
        self.scat.set_offsets(self.rain_drops['position'])

        return self.scat,


# From: https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html
class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)

        self.label_fps = QtWidgets.QLabel('0')
        layout.addWidget(self.label_fps)

        # Ideally one would use self.addToolBar here, but it is slightly
        # incompatible between PyQt6 and other bindings, so we just add the
        # toolbar as a plain widget instead.
        layout.addWidget(mplWidget())

        # dynamic_canvas = FigureCanvas(Figure(figsize=(5, 3)))
        # layout.addWidget(dynamic_canvas)
        # # layout.addWidget(NavigationToolbar(dynamic_canvas, self))

        # self._dynamic_ax = dynamic_canvas.figure.subplots()
        # t = np.linspace(0, 10, 101)
        # # Set up a Line2D.
        # self._line, = self._dynamic_ax.plot(t, np.sin(t + time.time()))
        # self._timer = dynamic_canvas.new_timer(100)
        # self._timer.add_callback(self._update_canvas)
        # self._timer.start()

        # From: https://stackoverflow.com/questions/51488701/python-desktop-fps-displaying-in-label
        # Add in creating and connecting the timer 
        self.timer = QTimer()
        self.timer.setInterval(100)  # 100 milliseconds = 0.1 seconds
        self.timer.timeout.connect(self.fps_display)  # Connect timeout signal to function
        self.timer.start()  # Set the timer running

    def _update_canvas(self):
        t = np.linspace(0, 10, 101)
        # Shift the sinusoid as a function of time.
        self._line.set_data(t, np.sin(t + time.time()))
        self._line.figure.canvas.draw()

    @pyqtSlot()  # Decorator to tell PyQt this method is a slot that accepts no arguments
    def fps_display(self):
        start_time = time.time()
        counter = 1
        # All the logic()
        # time.sleep(0.1)
        time_now = time.time()
        fps = (counter / (time_now - start_time))
        self.label_fps.setText(f"{fps:.2f} fps")


# if __name__ == '__main__':
#     app = QtGui.QApplication(sys.argv)
#     window = mplWidget()
#     sys.exit(app.exec_())

if __name__ == "__main__":
    # Check whether there is already a running QApplication (e.g., if running
    # from an IDE).
    qapp = QtWidgets.QApplication.instance()
    if not qapp:
        qapp = QtWidgets.QApplication(sys.argv)

    app = ApplicationWindow()
    app.show()
    app.activateWindow()
    app.raise_()
    qapp.exec()


# pl.start_processing()
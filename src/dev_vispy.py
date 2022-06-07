import sys
import numpy as np
from PyQt5 import QtWidgets

import vispy
import vispy.plot as vp

class TryToUpdatePlot(QtWidgets.QWidget):
    def __init__(self):
        super(TryToUpdatePlot, self).__init__()
        self.initUI()

    def initUI(self):
        # vispy
        data = np.random.rand(100, 2) # random data
        self.fig = vp.Fig(size=(800, 600))
        self.line1 = self.fig[0, 0].plot(data=data)
        self.line2 = self.fig[1, 0].plot(data=data)

        # PyQt (with vispy fig.native)
        self.myHBoxLayout = QtWidgets.QHBoxLayout(self)
        self.button = QtWidgets.QPushButton('My Button')
        self.myHBoxLayout.addWidget(self.button)
        self.myHBoxLayout.addWidget(self.fig.native)

        self.show()
        self.button.released.connect(self.handle_button)

    def handle_button(self):
        # update line1 plot with new data offset by 100
        newData = np.random.rand(100, 2) + 100
        self.line1.set_data(newData)

        # Is there something I can add here ???
        for line, pwidget in zip([self.line1, self.line2], self.fig.plot_widgets):
            x_data = line._line.pos[:, 0]
            y_data = line._line.pos[:, 1]
            x_range = x_data.min(), x_data.max()
            y_range = y_data.min(), y_data.max()

            pwidget.view.camera.set_range(x=x_range, y=y_range)
        self.update()

if __name__ == '__main__':
    appQt = QtWidgets.QApplication(sys.argv)
    myClasss = TryToUpdatePlot()
    vispy.app.run() # run vispy event loop, does not return
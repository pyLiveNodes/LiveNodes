import math
import sys

from vispy import gloo, app

from PyQt5 import QtWidgets

app.use_app("pyqt5")


class Canvas(app.Canvas):
    def __init__(self, *args, **kwargs):
        app.Canvas.__init__(self, *args, **kwargs)
        self._timer = app.Timer("auto", connect=self.on_timer, start=True)
        self.tick = 0

    def on_draw(self, event):
        gloo.clear(color=True)

    def on_timer(self, event):
        self.tick += 1 / 60.0
        c = abs(math.sin(self.tick))
        gloo.set_clear_color((c, c, c, 1))
        self.update()


class MyWindow(QtWidgets.QDialog):
    def __init__(self):
        super(MyWindow, self).__init__()

        self.canvas = Canvas()

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel('Test'))
        lay.addWidget(self.canvas.native)


if __name__ == "__main__":
    gui = QtWidgets.QApplication(sys.argv)
    w = MyWindow()
    w.show()
    app.run()
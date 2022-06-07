from functools import partial
import traceback
from livenodes.core import viewer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

from matplotlib.figure import Figure
from matplotlib import animation
import matplotlib.pyplot as plt
from PyQt5 import QtCore
from PyQt5.QtWidgets import QGridLayout, QWidget, QHBoxLayout
import multiprocessing as mp

from vispy import app as vp_app
import vispy.plot as vp
from vispy import scene
# vp_app.use_app('pyqt5')

from livenodes.core.node import Node

import seaborn as sns

sns.set_style("darkgrid")
sns.set_context("paper")

# TODO: make each subplot their own animation and use user customizable panels
# TODO: allow nodes to use qt directly -> also consider how to make this understandable to user (ie some nodes will not run everywhere then)

def node_view_mapper(parent, node):
    if isinstance(node, viewer.View_MPL):
        return Qt_node_mpl(node)
    elif isinstance(node, viewer.View_Vispy):
        return Qt_node_vispy(node, parent=parent)
    elif isinstance(node, viewer.View_QT):
        return Qt_node_qt(node, parent=parent)
    else:
        raise ValueError(f'Unkown Node type {str(node)}')

# adapted from: https://stackoverflow.com/questions/39835300/python-qt-and-matplotlib-scatter-plots-with-blitting
class Run(QWidget):

    def __init__(self, pipeline, parent=None):
        super().__init__(parent=parent)

        self.pipeline = pipeline

        # === Setup draw canvases =================================================
        self.qt_grid = QGridLayout(self)

        self.nodes = [n for n in Node.discover_graph(pipeline) if isinstance(n, viewer.View)]
        self.draw_widgets = list(map(partial(node_view_mapper, self), self.nodes))

        n_figs = len(self.draw_widgets)
        cols = min(3, n_figs)

        for i, (widget, node) in enumerate(zip(self.draw_widgets, self.nodes)):
            col = i % cols
            row = int((i - col) / cols)
            self.qt_grid.addWidget(widget.get_qt_widget(), row, col)
        
        # === Start pipeline =================================================
        self.worker_term_lock = mp.Lock()
        self.worker_term_lock.acquire()
        self.worker = mp.Process(target=self.worker_start)
        # self.worker.daemon = True
        self.worker.start()


    def worker_start(self):
        self.pipeline.start()
        self.worker_term_lock.acquire()

        print('Termination time in pipeline!')
        self.pipeline.stop()
        self.worker_term_lock.release()

    # i would have assumed __del__ would be the better fit, but that doesn't seem to be called when using del... for some reason
    # will be called in parent view, but also called on exiting the canvas
    def stop(self, *args, **kwargs):
        # Tell the process to terminate, then wait until it returns
        self.worker_term_lock.release()
        self.worker.join(2)

        # yes, sometimes the program will then not return, but only if we also really need to kill the subprocesses!
        self.worker_term_lock.acquire()
        # self.pipeline.stop()
        
        print('Termination time in view!')
        self.worker.terminate()

        print('Terminating draw widgets')
        for widget in self.draw_widgets:
            widget.stop()

class Qt_node_qt(QWidget):
    def __init__(self, node, parent=None):
        super().__init__(parent=parent)

        if not isinstance(node, viewer.View_QT):
            raise ValueError('Node must be of Type (Qt) View')

        node.init_draw(self)
    
    def get_qt_widget(self):
        return self
    
    def stop(self):
        pass

class Qt_node_vispy(QWidget):
    def __init__(self, node, parent=None):
        super().__init__(parent=parent)

        if not isinstance(node, viewer.View_Vispy):
            raise ValueError('Node must be of Type (Vispy) View')

        # self.fig = vp.Fig(size=(400, 300), app="pyqt5", show=False, parent=parent)
        # self.fig = vp.Fig(size=(400, 300), show=False, parent=parent)
        self.fig = scene.SceneCanvas(size=(400, 300), show=False, parent=parent, bgcolor='white')
        node_update_fn = node.init_draw(self.fig)

        def update(*args, **kwargs):
            nonlocal self, node_update_fn
            if node_update_fn():
                self.update()

        self._timer = vp_app.Timer('auto', connect=update, start=True)
    
    def get_qt_widget(self):
        return self.fig.native
    
    def stop(self):
        self._timer.stop()

# class Qt_node_vispy(vp_app.Canvas):
#     def __init__(self, node, parent=None, *args, **kwargs):
#         # no clue, why we cannot just use super().__init__ here....
#         vp_app.Canvas.__init__(self, app="pyqt5", parent=parent, *args, **kwargs)

#         if not isinstance(node, viewer.View_Vispy):
#             raise ValueError('Node must be of Type (Vispy) View')

#         self.fig = vp.Fig(size=(400, 300))
#         node_update_fn = node.init_draw(self.fig)

#         # layout = QHBoxLayout(self)
#         # layout.addWidget(fig.native)

#         # repeat forever, todo: figure out how to end this
#         # while True:
#         #     # the call to node_update_fn should block until there is something new to be rendered
#         #     re_render = node_update_fn()
#         #     if re_render:
#         #         self.update()
#         def update(*args, **kwargs):
#             nonlocal self, node_update_fn
#             if node_update_fn():
#                 self.update()

#         self._timer = vp_app.Timer('auto', connect=update, start=True)
#         # self.tick = 0

#     def on_timer(self, *args, **kwargs):
#         if self.node_update_fn():
#             self.update()
    
#     def get_qt_widget(self):
#         return self.native
    
#     def stop(self):
#         self._timer.stop()


class Qt_node_mpl(FigureCanvasQTAgg):

    def __init__(self, node, figsize=(4, 4), font = {'size': 10}, interval=0):
        super().__init__(Figure(figsize=figsize))

        if not isinstance(node, viewer.View_MPL):
            raise ValueError('Node must be of Type (MPL) View')

        plt.rc('font', **font)

        artist_update_fn = node.init_draw(self.figure)

        def draw_update(i, **kwargs):
            try:
                return artist_update_fn(i, **kwargs)
            except Exception as err:
                print(err)
                print(traceback.format_exc())
            return []

        self.animation = animation.FuncAnimation(fig=self.figure,
                                                 func=draw_update,
                                                 interval=interval,
                                                 blit=True)

        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.setFocus()
        
        # self.show()

    def get_qt_widget(self):
        return self

    def stop(self):
        self.animation.pause()


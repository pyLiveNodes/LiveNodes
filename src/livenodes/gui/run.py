import traceback
from livenodes.core import viewer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

from matplotlib.figure import Figure
from matplotlib import animation
import matplotlib.pyplot as plt
import time
from PyQt5 import QtCore
from PyQt5.QtWidgets import QHBoxLayout, QWidget
import multiprocessing as mp

from livenodes.core.node import Node

import seaborn as sns

sns.set_style("darkgrid")
sns.set_context("paper")

# TODO: make each subplot their own animation and use user customizable panels
# TODO: allow nodes to use qt directly -> also consider how to make this understandable to user (ie some nodes will not run everywhere then)

def node_view_mapper(node):
    if isinstance(node, viewer.View_MPL):
        return MPL_View(node)
    elif isinstance(node, viewer.View_QT):
        return QT_View(node)
    else:
        raise ValueError(f'Unkown Node type {str(node)}')

# adapted from: https://stackoverflow.com/questions/39835300/python-qt-and-matplotlib-scatter-plots-with-blitting
class Run(QWidget):

    def __init__(self, pipeline, parent=None):
        super().__init__(parent=parent)

        self.pipeline = pipeline

        # === Setup draw canvases =================================================
        # self.timer = time.time()

        # TODO: let nodes explizitly declare this!
        # TODO: while we're at it: let nodes declare available/required input and output streams
        # the following works because the str representation of each node in a pipline must be unique
        self.draw_widgets = {
            str(n): node_view_mapper(node=n)
            for n in Node.discover_graph(pipeline) if isinstance(n, viewer.View)
        }.values()

        self.qt_grid = QHBoxLayout(self)
        for widget in self.draw_widgets:
            self.qt_grid.addWidget(widget)

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

class QT_View(QWidget):
    def __init__(self, node, parent=None):
        super().__init__(parent=parent)

        if not isinstance(node, viewer.View_QT):
            raise ValueError('Node must be of Type (MPL) View')

        node.init_draw(self)
    
    def stop(self):
        pass


class MPL_View(FigureCanvasQTAgg):

    def __init__(self, node, figsize=(4, 4), font = {'size': 10}, interval=0):
        super().__init__(Figure(figsize=figsize))

        if not isinstance(node, viewer.View_MPL):
            raise ValueError('Node must be of Type (MPL) View')

        plt.rc('font', **font)

        # https://matplotlib.org/stable/gallery/subplots_axes_and_figures/subfigures.html
        # subfigs = self.figure.subfigures(rows, cols)  #, wspace=1, hspace=0.07)
        # we might create subfigs, but if each node has it's own qwidget, we do not need to and can instead just pass the entire figure
        artist_update_fn = node.init_draw(self.figure)

        def draw_update(i, **kwargs):
            try:
                return artist_update_fn(**kwargs)
            except Exception as err:
                print(err)
                print(traceback.format_exc())
            return []

            # # TODO: move this into a node :D
            # if i % 100 == 0 and i != 0:
            #     el_time = time.time() - self.timer
            #     self.fps = i / el_time
            #     print(
            #         f"Rendered {i} frames in {el_time:.2f} seconds. This equals {self.fps:.2f}fps."
            #     )

        self.animation = animation.FuncAnimation(fig=self.figure,
                                                 func=draw_update,
                                                 interval=interval,
                                                 blit=True)

        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.setFocus()
        
        self.show()

    def stop(self):
        self.animation.pause()


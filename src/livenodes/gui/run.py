from livenodes.core import viewer

from PyQt5.QtWidgets import QGridLayout
import multiprocessing as mp

from livenodes.core.node import Node
from .components.node_views import node_view_mapper
from .pages.page import Page

# adapted from: https://stackoverflow.com/questions/39835300/python-qt-and-matplotlib-scatter-plots-with-blitting
class Run(Page):

    def __init__(self, pipeline, parent=None):
        super().__init__(parent=parent)

        self.pipeline = pipeline

        # === Setup draw canvases =================================================
        self.nodes = [n for n in Node.discover_graph(pipeline) if isinstance(n, viewer.View)]
        self.draw_widgets = list(map(node_view_mapper, self.nodes))

        n_figs = len(self.draw_widgets)
        cols = min(3, n_figs)

        self.qt_grid = QGridLayout(self)
        widget_positions = {} # TODO: implement saving loading this to a file
        for i, (widget, node) in enumerate(zip(self.draw_widgets, self.nodes)):
            col = i % cols
            row = int((i - col) / cols)
            widget_positions[str(node)] = (row, col)
            self.qt_grid.addWidget(widget, row, col)
        
        print(widget_positions)

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

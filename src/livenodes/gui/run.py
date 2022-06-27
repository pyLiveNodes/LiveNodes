from functools import partial
from livenodes.core import viewer
import os
import json

from PyQt5.QtWidgets import QHBoxLayout
from PyQt5 import QtCore

from PyQtAds import QtAds

import multiprocessing as mp

from livenodes.core.node import Node
from .components.node_views import node_view_mapper
from .components.page import Page, Action, ActionKind

# adapted from: https://stackoverflow.com/questions/39835300/python-qt-and-matplotlib-scatter-plots-with-blitting
class Run(Page):

    def __init__(self, pipeline_path, pipeline, parent=None):
        super().__init__(parent=parent)

        self.pipeline = pipeline
        self._create_paths(pipeline_path)

        # === Setup draw canvases =================================================
        self.nodes = [n for n in Node.discover_graph(pipeline) if isinstance(n, viewer.View)]
        self.draw_widgets = list(map(node_view_mapper, self.nodes))
        
        QtAds.CDockManager.setConfigFlag(QtAds.CDockManager.XmlCompressionEnabled, False)
        
        self.layout = QHBoxLayout(self)
        self.dock_manager = QtAds.CDockManager(self)
        self.layout.addWidget(self.dock_manager)
        self.widgets = []

        for widget, node in zip(self.draw_widgets, self.nodes):
            dock_widget = QtAds.CDockWidget(node.name)
            self.widgets.append(dock_widget)
            dock_widget.viewToggled.connect(partial(print, '=======', str(node), "qt emitted signal"))
            dock_widget.setWidget(widget)
            dock_widget.setFeature(QtAds.CDockWidget.DockWidgetClosable, False)

            self.dock_manager.addDockWidget(QtAds.RightDockWidgetArea, dock_widget)

        if os.path.exists(self.pipeline_gui_path):
            with open(self.pipeline_gui_path, 'r') as f:
                self.dock_manager.restoreState(QtCore.QByteArray(f.read().encode()))

        # restore might remove some of the newly added widgets -> add it back in here
        for widget, node in zip(self.widgets, self.nodes):
            if widget.isClosed():
                # print('----', str(node))
                widget.setClosedState(False)
                self.dock_manager.addDockWidget(QtAds.RightDockWidgetArea, widget)


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

    def get_actions(self):
        return [ \
            Action(label="Back", fn=self.save, kind=ActionKind.BACK),
            # Action(label="Cancel", kind=ActionKind.BACK),
        ]

    def save(self):
        with open(self.pipeline_gui_path, 'w') as f:
            f.write(self.dock_manager.saveState().data().decode())

    def _create_paths(self, pipeline_path):
        self.pipeline_path = pipeline_path
        self.pipeline_gui_path = pipeline_path.replace('/pipelines/', '/gui/', 1).replace('.json', '_dock.xml')

        gui_folder = '/'.join(self.pipeline_gui_path.split('/')[:-1])
        if not os.path.exists(gui_folder):
            os.mkdir(gui_folder)
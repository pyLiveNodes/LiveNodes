import traceback
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

import matplotlib
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib import animation
import matplotlib.pyplot as plt
import math
import numpy as np
import time

from PyQt5 import QtWidgets, QtCore
import sys

import asyncio 
import multiprocessing as mp
import threading

from src.nodes.node import Node, View

import seaborn as sns
sns.set_style("darkgrid")
sns.set_context("paper")


# TODO: make each subplot their own animation and use user customizable panels
# TODO: allow nodes to use qt directly -> also consider how to make this understandable to user (ie some nodes will not run everywhere then)


# adapted from: https://stackoverflow.com/questions/39835300/python-qt-and-matplotlib-scatter-plots-with-blitting
class Run(FigureCanvasQTAgg):
    def __init__(self, pipeline):
        super().__init__(Figure(figsize=(12, 10)))

        self.pipeline = pipeline

        self.setupAnim(self.pipeline)

        self.setFocusPolicy( QtCore.Qt.ClickFocus )
        self.setFocus()

        self.worker_term_lock = mp.Lock()
        self.worker_term_lock.acquire()
        self.worker = mp.Process(target = self.worker_start)
        # self.worker.daemon = True
        self.worker.start()

        self.show()

    def worker_start(self):
        self.pipeline.start()
        self.worker_term_lock.acquire()

        print('Termination time in pipeline!')
        self.pipeline.stop()


    # i would have assumed __del__ would be the better fit, but that doesn't seem to be called when using del... for some reason
    # will be called in parent view, but also called on exiting the canvas
    def stop(self, *args, **kwargs):
        # Tell the process to terminate, then wait until it returns
        self.worker_term_lock.release()
        self.worker.join(3)

        print('Termination time in view!')
        self.worker.terminate()
        self.animation.pause()


    def setupAnim(self, pipeline):
        self.timer = time.time()

        font={'size': 10}

        # TODO: let nodes explizitly declare this! 
        # TODO: while we're at it: let nodes declare available/required input and output streams
        # the following works because the str representation of each node in a pipline must be unique
        draws = {str(n): n.init_draw for n in Node.discover_childs(pipeline) if isinstance(n, View)}.values()
        # print(draws)

        plt.rc('font', **font)

        # fig.suptitle("ASK", fontsize='x-large')
        # self.figure.canvas.manager.set_window_title("ASK")
        self.figure.canvas.mpl_connect("close_event", self.stop)

        if len(draws) <= 0:
            raise Exception ('Must have at least one draw function registered')

        n_figs = len(draws)
        cols = min(3, n_figs)
        rows = math.ceil(n_figs / cols) # ie max 3 columns

        # https://matplotlib.org/stable/gallery/subplots_axes_and_figures/subfigures.html
        subfigs = self.figure.subfigures(rows, cols) #, wspace=1, hspace=0.07)

        if len(draws) == 1:
            subfigs = [subfigs] # matplotlibs subfigures call doesn't consistently return a list, but with n=1 the subfig directly...
        subfigs = np.array(subfigs).flatten()

        artists = [setup_fn(subfig) for setup_fn, subfig in zip(draws, subfigs)]

        # not nice, as cannot be updated at runtime later on (not sure if that'll be necessary tho)
        def draw_update (i, **kwargs):
            ret_arts = []
            for fn in artists:
                try:
                    ret_arts.extend(fn(**kwargs))
                except Exception as err:
                    print(err)
                    print(traceback.format_exc())

            # TODO: move this into a node :D
            if i % 100 == 0 and i != 0:
                el_time = time.time() - self.timer
                self.fps = i/el_time
                print(f"Rendered {i} frames in {el_time:.2f} seconds. This equals {self.fps:.2f}fps.")

            return ret_arts

        self.animation = animation.FuncAnimation(fig=self.figure, func=draw_update, interval=0, blit=True)

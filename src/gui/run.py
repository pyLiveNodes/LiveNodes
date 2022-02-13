from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

import matplotlib
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib import animation
import matplotlib.pyplot as plt
import math
import numpy as np
import time

from PyQt6 import QtWidgets
import sys

from multiprocessing import Process


# # TODO: as we now have a qt part here, we could add a qlabel with the fps...
# class Run(QWidget):
#     def __init__(self, pipeline, parent=None):
#         super().__init__(parent)

#         self.canvas = Animation(pipeline=pipeline)

#         worker = Process(target = pipeline.start_processing)
#         worker.daemon = True
#         worker.start()


# adapted from: https://stackoverflow.com/questions/39835300/python-qt-and-matplotlib-scatter-plots-with-blitting
class Run(FigureCanvasQTAgg):
    def __init__(self, pipeline):
        super().__init__(Figure(figsize=(12, 7.5)))

        self.pipeline = pipeline

        self.setupAnim(self.pipeline)

        self.worker = Process(target = self.pipeline.start_processing)
        self.worker.daemon = True
        self.worker.start()

        self.show()

    # i would have assumed __del__ would be the better fit, but that doesn't seem to be called when using del... for some reason
    def stop (self):
        print("called stop")
        self.pipeline.stop_processing()
        self.worker.terminate()
        self.animation.pause()

    def setupAnim(self, pipeline):
        self.timer = time.time()

        font={'size': 6}

        # TODO: let nodes explizitly declare this! 
        # TODO: while we're at it: let nodes declare available/required input and output streams
        # the following works because the str representation of each node in a pipline must be unique
        draws = {str(n): n.init_draw for n in pipeline.discover_childs(pipeline) if hasattr(n, 'init_draw')}.values()
        # print(draws)

        plt.rc('font', **font)

        # fig.suptitle("ASK", fontsize='x-large')
        # self.figure.canvas.manager.set_window_title("ASK")
        self.figure.canvas.mpl_connect("close_event", pipeline.stop_processing)

        if len(draws) <= 0:
            raise Exception ('Must have at least one draw function registered')

        n_figs = len(draws)
        cols = min(2, n_figs)
        rows = math.ceil(n_figs / cols) # ie max 3 columns

        # https://matplotlib.org/stable/gallery/subplots_axes_and_figures/subfigures.html
        subfigs = self.figure.subfigures(rows, cols) #, wspace=1, hspace=0.07)

        if len(draws) == 1:
            subfigs = [subfigs] # matplotlibs subfigures call doesn't consistently return a list, but with n=1 the subfig directly...
        subfigs = np.array(subfigs).flatten()

        artists = [setup_fn(subfig) for setup_fn, subfig in zip(draws, subfigs)]

        # not nice, as cannot be updated at runtime later on (not sure if that'll be necessary tho)
        def draw_update (i, **kwargs):
            ret_arts = list(np.concatenate([fn(**kwargs) for fn in artists], axis=0))

            if i % 100 == 0 and i != 0:
                el_time = time.time() - self.timer
                self.fps = i/el_time
                print(f"Rendered {i} frames in {el_time:.2f} seconds. This equals {self.fps:.2f}fps.")

            return ret_arts

        self.animation = animation.FuncAnimation(fig=self.figure, func=draw_update, interval=0, blit=True)

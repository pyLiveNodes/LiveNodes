from functools import partial
from matplotlib import animation

from src.nodes.node import Node, activate_timing

import numpy as np
import matplotlib.pyplot as plt
import matplotlib

import time
from threading import Thread
from multiprocessing import Process
import multiprocessing as mp

import math

# from src.realtime_animation import RealtimeAnimation

import seaborn as sns
sns.set_style("darkgrid")
sns.set_context("paper")

matplotlib.rcParams['toolbar'] = 'None'

if __name__ == '__main__':

    print('=== Load Pipeline ====')
    pipeline = Node.load('pipelines/features.json')

    print('=== Start main loops ====')

    font={'size': 6}

    draws = {str(n): n.init_draw for n in Node.discover_childs(pipeline) if hasattr(n, 'init_draw')}.values()
    print(draws)

    plt.rc('font', **font)

    fig = plt.figure(num=0, figsize=(12, 7.5))
    # fig.suptitle("ASK", fontsize='x-large')
    fig.canvas.manager.set_window_title("ASK")

    if len(draws) <= 0:
        raise Exception ('Must have at least one draw function registered')

    n_figs = len(draws)
    cols = min(2, n_figs)
    rows = math.ceil(n_figs / cols) # ie max 3 columns

    # https://matplotlib.org/stable/gallery/subplots_axes_and_figures/subfigures.html
    subfigs = fig.subfigures(rows, cols) #, wspace=1, hspace=0.07)

    if len(draws) == 1:
        subfigs = [subfigs] # matplotlibs subfigures call doesn't consistently return a list, but with n=1 the subfig directly...
    subfigs = np.array(subfigs).flatten()

    # artists = np.concatenate([setup_fn(subfig) for setup_fn, subfig in zip(draws, subfigs)])
    artists = [setup_fn(subfig) for setup_fn, subfig in zip(draws, subfigs)]

    # not nice, as cannot be updated at runtime later on (not sure if that'll be necessary tho)
    def draw_update (i, **kwargs):
        ret_arts = list(np.concatenate([fn(**kwargs) for fn in artists], axis=0))

        if i % 100 == 0 and i != 0:
            el_time = time.time() - timer
            print(f"Rendered {i} frames in {el_time:.2f} seconds. This equals {i/el_time:.2f}fps.")

        return ret_arts


    timer = time.time()
    pipeline.start_processing()

    # animationProcess = animation.FuncAnimation(fig=fig, func=draw_update, interval=0, blit=True)
    # fig.canvas.mpl_connect("close_event", pipeline.stop_processing)

    # plt.show()

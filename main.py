from matplotlib import animation
from src.nodes.blit import BlitManager

from src.nodes.node import Node, activate_timing

import numpy as np
import matplotlib.pyplot as plt

import time
import threading
from multiprocessing import Process

import math

# from src.realtime_animation import RealtimeAnimation

TIME = False

print('=== Load Pipeline ====')
if TIME: activate_timing()
pipeline = Node.load('pipelines/preprocess.json')


print('=== Start main loops ====')

font={'size': 6}

# TODO: let nodes explizitly declare this! 
# TODO: while we're at it: let nodes declare available/required input and output streams
# works because the str representation of each node in a pipline must be unique
draws = {str(n): n.init_draw for n in Node.discover_nodes(pipeline) if hasattr(n, 'init_draw')}.values()
print(draws)

plt.rc('font', **font)

fig = plt.figure(num=0, figsize =(16, 10))
# fig.suptitle("ASK", fontsize='x-large')
fig.canvas.manager.set_window_title("ASK")
fig.canvas.mpl_connect("close_event", pipeline.stop_processing)

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
# bm = BlitManager(fig.canvas, artists)

# plt.show(block=False)
# plt.pause(.1)

# not nice, as cannot be updated at runtime later on (not sure if that'll be necessary tho)
def draw_update (i, **kwargs):
    ret_arts = list(np.concatenate([fn(**kwargs) for fn in artists], axis=0))

    if i % 100 == 0 and i != 0:
        el_time = time.time() - timer
        print(f"Rendered {i} frames in {el_time:.2f} seconds. This equals {i/el_time:.2f}fps.")

    return ret_arts


# Threading example
# worker = threading.Thread(target = pipeline.start_processing)
# worker.daemon = True
# worker.start()

worker = Process(target = pipeline.start_processing)
worker.daemon = True
worker.start()

# initial_draw_and_setup()
timer = time.time()

animationProcess = animation.FuncAnimation(fig=fig, func=draw_update, interval=1, blit=True)
# plt.tight_layout()
plt.show()

# import matplotlib as mpl 
# mpl.rcParams['animation.ffmpeg_path'] = '/usr/bin/ffmpeg'
# animationProcess = animation.FuncAnimation(fig=fig, frames=200, save_count=200, func=update, interval=1, blit=True)
# writervideo = animation.FFMpegWriter(fps=7) 
# animationProcess.save("demo.mp4", writer=writervideo)

# worker.join()


pipeline.make_dot_graph().save('current.png')

if TIME:
    # see https://gitlab.csl.uni-bremen.de/bioguitar/livenodes/-/blob/master/notebooks/NewInterfaceTest.ipynb
    # for an example how to plot 
    print(pipeline.get_timing_info())

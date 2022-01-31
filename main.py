from matplotlib import animation
from src.nodes.blit import BlitManager
from src.nodes.playback import Playback
from src.nodes.draw_lines import Draw_lines
from src.nodes.node import load

import numpy as np
import matplotlib.pyplot as plt

import time
import threading

import math

# from src.realtime_animation import RealtimeAnimation

print('=== Load Pipeline ====')
pipeline = load('pipelines/recognize.json')


print('=== Start main loops ====')

font={'size': 6}

def collect_init_draw(node):
    res = []
    if hasattr(node, 'init_draw'):
        res.append(node.init_draw)
    for n in node.output_classes:
        res.extend(collect_init_draw(n))
    return res

draws = collect_init_draw(pipeline)
print(draws)

plt.rc('font', **font)

fig = plt.figure(num=0, figsize =(20, 5))
# fig.suptitle("ASK", fontsize='x-large')
fig.canvas.manager.set_window_title("ASK")
fig.canvas.mpl_connect("close_event", pipeline.stop_processing)

if len(draws) <= 0:
    raise Exception ('Must have at least one draw function registered')

n_figs = len(draws)
cols = min(3, n_figs)
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
n_frames_rendered = 0
def draw_update (i, **kwargs):
    global n_frames_rendered
    n_frames_rendered = i
    return list(np.concatenate([fn(**kwargs) for fn in artists], axis=0))

worker = threading.Thread(target = pipeline.start_processing)
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

el_time = time.time() - timer
print(f"Rendered {n_frames_rendered} frames in {el_time:.2f} seconds. This equals {n_frames_rendered/el_time:.2f}fps.")
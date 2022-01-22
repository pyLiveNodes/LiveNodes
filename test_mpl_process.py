# from: https://gitpress.io/@natamacm/matplotlib-example-animation-process-example

import multiprocessing as mp

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


def animproc(func, frames=None, new_fig=None, daemon=True, blit=None, interval=30):
    if new_fig is None:
        new_fig = plt.figure

    def target():
        fig = new_fig()
        _ = FuncAnimation(fig, func, frames=frames, fargs=(fig,), blit=blit, interval=interval)
        plt.show()

    proc = mp.Process(target=target)
    proc.daemon = daemon
    return proc


def _main():
    import time
    import numpy as np

    def _new_fig():
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.margins(x=.01, y=.01)
        ax.plot([], [], '+')
        return fig

    def _update_fig(frame, fig):
        ax = fig.axes[0]
        line = ax.lines[0]
        line.set_xdata(frame[0])
        line.set_ydata(frame[1])

        ax.relim()
        ax.autoscale()

    queue = mp.Queue(1)
    process = animproc(_update_fig, frames=iter(queue.get, None), new_fig=_new_fig)
    process.start()

    t0 = time.time()
    x, y = [], []
    while process.is_alive() and time.time() - t0 < 10:
        x.append(time.time() - t0)
        y.append(np.sin(5 * x[-1]))
        time.sleep(0.01)

        if queue.empty():
            queue.put([x, y])


if __name__ == '__main__':
    _main()
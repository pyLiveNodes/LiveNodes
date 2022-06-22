import traceback
from livenodes.core import viewer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

from matplotlib.figure import Figure
from matplotlib import animation
import matplotlib.pyplot as plt
from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QTimer


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


class QT_View(QWidget):
    def __init__(self, node, parent=None):
        super().__init__(parent=parent)

        if not isinstance(node, viewer.View_QT):
            raise ValueError('Node must be of Type (MPL) View')

        # self.setStyleSheet("QWidget { background-color: 'white' }") 
        self.setProperty("cssClass", "bg-white")
        artist_update_fn = node.init_draw(self)

        if artist_update_fn is not None:
            self.timer = QTimer(self)
            self.timer.setInterval(10) # max 100fps
            self.timer.timeout.connect(artist_update_fn)
            self.timer.start()

        # self.setBackgroundRole(True)
        # p = self.palette()
        # p.setColor(self.backgroundRole(), Qt.white)
        # self.setPalette(p)
    
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
                return artist_update_fn(i, **kwargs)
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


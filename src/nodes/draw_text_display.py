import collections
from queue import Queue
from tkinter import N
import numpy as np

from .node import Node

import matplotlib.patches as mpatches

import multiprocessing as mp
import ctypes as c

import time

class Draw_text_display(Node):
    # TODO: move the sample rate into a data_stream?
    def __init__(self, initial_text="", name = "Text Output", dont_time = False):
        super().__init__(name=name, has_outputs=False, dont_time=dont_time)

        self.text_queue = mp.SimpleQueue()
        self.text = initial_text

    @staticmethod
    def info():
        return {
            "class": "Draw_text_display",
            "file": "Draw_text_display.py",
            "in": ["Text",],
            "out": [],
            "init": {
                "name": "Name"
            },
            "category": "Draw"
        }
        
    @property
    def in_map(self):
        return {
            "Text": self.receive_data,
        }

    def _empty_queue(self, queue):
        res = None
        while not queue.empty():
            res = queue.get()
        return res


    def init_draw(self, subfig):
        subfig.suptitle(self.name, fontsize=14)
        ax = subfig.subplots(1, 1)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.set_xticks([])
        ax.set_yticks([])


        self.label = ax.text(0.005, 0.95, self.text, zorder=100, fontproperties=ax.xaxis.label.get_font_properties(), rotation='horizontal', va='top', ha='left', transform = ax.transAxes)

        def update (**kwargs):
            nonlocal self

            old_text = self.text
            while not self.text_queue.empty():
                self.text = self.text_queue.get()

            if old_text != self.text:
                self.label.set_text(self.text)

            return [self.label]
        return update


    def receive_data(self, data_frame, **kwargs):
        self.text_queue.put(data_frame)  

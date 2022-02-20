import collections
import numpy as np

from .node import Node

import time
from itertools import groupby
import seaborn as sns

import multiprocessing as mp



class Draw_gmm(Node):
    def __init__(self, plot_names=[], name = "GMM", dont_time = False):
        super().__init__(name=name, has_outputs=False, dont_time=dont_time)

        self.queue_meta = mp.Queue()
        self.queue_hypo = mp.Queue()
        self.queue_data = mp.Queue()

        self.graph = None
        self.topology = None

        self.name = name
        self.plot_names = plot_names

        self.bar_objs = []
        self.previous_alphas = []
        self.token_node_map = {}

    
    @staticmethod
    def info():
        return {
            "class": "Draw_gmm",
            "file": "draw_gmm.py",
            "in": ["HMM Meta", "Hypothesis"],
            "out": [],
            "init": {
                "name": "Name"
            },
            "category": "Draw"
        }
        
    @property
    def in_map(self):
        return {
            "HMM Meta": self.receive_meta,
            "Hypothesis": self.receive_hypo,
            "Data": self.receive_data
        }

    def _get_setup(self):
        return {\
            "name": self.name,
            "plot_names": self.plot_names
           }


    def _setup_axes(self, subfig):
        update_fn_preprocessed = self._draw_preprocessed_helper(ax, self.idx, self.plot_names)
        
    def _empty_queue(self, queue):
        res = None
        while not queue.empty():
            res = queue.get()
        return res

    # TODO: make this it's own class
    def _draw_preprocessed_helper(self, ax, idx, names, n_scatter_points = 10):
        xData = [0] * n_scatter_points 
        yData = [0] * n_scatter_points
        alphas = np.linspace(0.1, 1, n_scatter_points)

        ax.set_xlabel(names[0])
        ax.set_ylabel(names[1])

        scatter = ax.scatter(xData, yData, alpha=alphas)

        # this way all the draw details are hidden from everyone else
        # TODO: make this expect python/numpy arrays instead of biokit 
        def update(processedData, **kwargs):
            nonlocal xData, yData # no clue why this is needed here, but not the draw and update funcitons...
            if processedData != None:
                processedMcfs = processedData.getMatrix().T[idx[:2]]
                xData.extend(processedMcfs[0])
                xData = xData[-n_scatter_points:]
                yData.extend(processedMcfs[1])
                yData = yData[-n_scatter_points:]

                data = np.hstack((np.array(xData)[:,np.newaxis], np.array(yData)[:, np.newaxis]))
                scatter.set_offsets(data)
                return [scatter]
            return [scatter]
        return update

    def init_draw(self, subfig):
        self.ax = subfig.subplots(1, 1)
        self.ax.set_xlim(-1.1, 1.1)
        self.ax.set_ylim(-1.1, 1.1)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)

        subfig.suptitle("Gaussian Mixture Models", fontsize=14)
        
        def update (**kwargs):
            nonlocal self, subfig
    
            alpha_val = 0.5

            meta = self._empty_queue(self.queue_meta)
            hypo = self._empty_queue(self.queue_hypo)
            data = self._empty_queue(self.data)

            if meta is not None and not self._axes_setup:
                self.graph = meta.get('search_graph')
                self.topology = meta.get('topology')
                self.tokens = list(self.topology.keys())

                self.token_colors, self.atom_colors, self.state_colors = self._init_colors(self.topology)

                self._setup_axes(subfig)
                self._axes_setup = True
            
            # print('Update', self._axes_setup, self.graph is not None)
            
            if self._axes_setup and hypo is not None:
                state_ids = hypo[:3]

                if len(state_ids) > 0:
                for model_name, ells in model_ell_map.items():
                    if model_name in state_ids[:3]:
                        for ell in ells:
                            ell.set_visible(True)
                            # ell.set_color(self.order_colors[state_ids.index(model_name)])                    
                    else:
                        for ell in ells:
                            ell.set_visible(False)

                return ells_list + update_fn_preprocessed(processedData)
            return update_fn_preprocessed(processedData)
        return update

    def receive_meta(self, meta, **kwargs):
        self.queue_meta.put(meta)

    def receive_hypo(self, hypo, **kwargs):
        self.queue_hypo.put(hypo)
    
    def receive_data(self, data, **kwargs):
        self.queue_data.put(data)

    # TODO: share these between the different hmm draws...
    def _init_colors(self, topology):
        c = sns.color_palette("deep", len(topology))
        _state_colors = dict(zip(range(3), ['#b9b9b9', '#777777', '#3b3b3b'])) # bold assumption, that there are never more than 3 states
        _token_colors = dict(zip(topology.keys(), c))
        _atom_colors = {}
        for token, color in _token_colors.items():
            token_model = np.unique(topology[token])
            brightness_mod = list(reversed(np.linspace(0.8, 0.2, len(token_model)))) # this way with len=1 we use 0.8 instead of 0.2
            for i, atom in enumerate(token_model):
                _atom_colors[atom] = tuple([cc * brightness_mod[i] for cc in color])

        # To be save if a stream is missing, although likely more will break in that case.
        if '' not in _state_colors: _state_colors[''] = '#b9b9b9'
        if '' not in _token_colors: _token_colors[''] = '#b9b9b9'
        if '' not in _atom_colors: _atom_colors[''] = '#b9b9b9'

        return _token_colors, _atom_colors, _state_colors


import collections
import numpy as np

from .node import Node

import time
from itertools import groupby
import seaborn as sns

import multiprocessing as mp
import matplotlib as mpl



class Draw_gmm(Node):
    channels_in = ["Data", "Channel Names", "HMM Meta", "Hypo States", "GMM Models", "GMM Means", "GMM Covariances", "GMM Weights"],
    channels_out = []

    category = "Draw"
    description = "" 

    example_init = {
        "name": "GMM",
            "plot_names": ["Channel 1", "Channel 2"],
            "n_mixtures": 2,
            "n_scatter_points": 10,
            "name": "GMM"
    }

    # TODO: remove the plot_names filter! this should just be a step in the pipeline
    # (this entails fixing the gmms not being passed in the hmm meta stream but a stream of their own)

    # Stopped at: re-implementing plot_names in order to get this f**ing working for tomorrow
    def __init__(self, plot_names, n_mixtures=2, n_scatter_points = 10, name = "GMM", **kwargs):
        super().__init__(name=name, **kwargs)

        self.queue_meta = mp.Queue()
        self.queue_hypo = mp.Queue()
        self.queue_data = mp.Queue()
        self.queue_gmm_models = mp.Queue()
        self.queue_gmm_means = mp.Queue()
        self.queue_gmm_covs = mp.Queue()
        self.queue_gmm_weights = mp.Queue()
        self.queue_channels = mp.Queue()

        self.graph = None
        self.topology = None

        self.plot_names = plot_names
        self.idx = None
        self.n_scatter_points = n_scatter_points
        self.n_mixtures = n_mixtures
        self.update_scatter_fn = None
        self.model_ell_map = None
        self.ells_list = None

        self.bar_objs = []
        self.previous_alphas = []
        self.token_node_map = {}

        self.token_colors, self.atom_colors, self.state_colors = None, None, None
        self.gmms = None


    def _settings(self):
        return {\
            "name": self.name,
            "plot_names": self.plot_names,
            "n_scatter_points": self.n_scatter_points,
            "n_mixtures": self.n_mixtures
           }

    def _init_draw(self, subfig):
        self.ax = subfig.subplots(1, 1)
        self.ax.set_xlim(-0.5, 0.5)
        self.ax.set_ylim(-0.5, 0.5)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)

        self.ax.set_xlabel(self.plot_names[0])
        self.ax.set_ylabel(self.plot_names[1])

        subfig.suptitle(self.name, fontsize=14)
        
        def update (**kwargs):
            nonlocal self, subfig

            meta = None
            state_ids = None
            data = None
            if self.idx is not None: 
                # only read the meta and prew_draw the gmms if we have created the idx (which we need the channel names for)
                meta = self._empty_queue(self.queue_meta)
                state_ids = self._empty_queue(self.queue_hypo)
                data = self._empty_queue(self.queue_data)

                # TODO: THIS is a problem!
                # We can never be sure these are all set at the same time, as the queue filling and matplotlib render are completely independent processes
                # yes, in the fill part the calls are basically syncronus, but the render process can still be called in between the queues!
                # gmm_models = self._empty_queue(self.queue_gmm_models)
                # gmm_means = self._empty_queue(self.queue_gmm_means)
                # gmm_covs = self._empty_queue(self.queue_gmm_covs)
                # gmm_weights = self._empty_queue(self.queue_gmm_weights)
            channel_names = self._empty_queue(self.queue_channels)
            # gmms = self._empty_queue(self.queue_gmms) # TODO: consider separate stream for this (pro: can use filter, and can visualize training, con: complicated)

            if channel_names is not None and self.update_scatter_fn is None:
                self.update_scatter_fn = self._draw_preprocessed_helper(self.ax, channel_names, self.n_scatter_points)
                self.idx = [channel_names.index(x) for x in self.plot_names]

            if meta is not None and self.token_colors is None:
                self.token_colors, self.atom_colors, self.state_colors = self._init_colors(meta["topology"])
                self.gmms = meta.get('gmms')
            # if self.gmms is not None and self.ells_list is None:
                self.model_ell_map = {model_name: self._pre_draw_gmm(self.ax, model_name, m["means"], m["covariances"], m["mixture_weights"]) for model_name, m in self.gmms.items() }
                self.ells_list = list(np.concatenate(list(self.model_ell_map.values()), axis=0))
            
            if state_ids is not None and len(state_ids) > 0 and self.model_ell_map is not None:
                for model_name, ells in self.model_ell_map.items():
                    if model_name in state_ids[:self.n_mixtures]:
                        for ell in ells:
                            ell.set_visible(True)
                            # ell.set_color(self.order_colors[state_ids.index(model_name)])                    
                    else:
                        for ell in ells:
                            ell.set_visible(False)


            if self.update_scatter_fn is not None:
                if self.ells_list is not None:
                    return self.ells_list + self.update_scatter_fn(data)
                return self.update_scatter_fn(data)
            return []
        return update



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

    def _hack_get_atom_from_model_id(self, model_id):
        return '-'.join(model_id.split('-')[:-1])

    def _pre_draw_gmm(self, ax, model_id, means, covariance, mixture_weights):
        ells = []

        n_gaussians = len(means)
        for i in range(n_gaussians):
            # with lots of help from: https://scikit-learn.org/stable/auto_examples/mixture/plot_gmm_covariances.html
            # covariances = np.diag(gmm.getCovariance(i).getData()[idx[:2]])
            covariances = np.diag(covariance[i][self.idx])
            v, w = np.linalg.eigh(covariances)
            u = w[0] / np.linalg.norm(w[0])
            angle = np.arctan2(u[1], u[0])
            angle = 180 * angle / np.pi  # convert to degrees
            v = 2.0 * np.sqrt(2.0) * np.sqrt(v)

            ell = mpl.patches.Ellipse(means[i][self.idx], v[0], v[1], 180 + angle, color=self.atom_colors[self._hack_get_atom_from_model_id(model_id)])
            ell.set_label(model_id)
            ell.set_zorder(1)
            ell.set_alpha(mixture_weights[i])
            ell.set_clip_box(ax.bbox)

            ell.set_visible(False)
            ax.add_patch(ell)
            ells.append(ell)
        return ells

    # TODO: make this it's own class
    def _draw_preprocessed_helper(self, ax, names, n_scatter_points = 10):
        xData = [0] * n_scatter_points 
        yData = [0] * n_scatter_points
        alphas = np.linspace(0.1, 1, n_scatter_points)

        scatter = ax.scatter(xData, yData, alpha=alphas)

        # this way all the draw details are hidden from everyone else
        # TODO: make this expect python/numpy arrays instead of biokit 
        def update(processedData, **kwargs):
            nonlocal xData, yData # no clue why this is needed here, but not the draw and update funcitons...
            if processedData != None:
                processedMcfs = processedData.getMatrix().T[self.idx] # just use the first two, filter does change the order of the channels, so that should be used if specific channels shall be plotted
                xData.extend(processedMcfs[0])
                xData = xData[-(n_scatter_points + 1):]
                yData.extend(processedMcfs[1])
                yData = yData[-(n_scatter_points + 1):]

                data = np.hstack((np.array(xData)[:,np.newaxis], np.array(yData)[:, np.newaxis]))
                scatter.set_offsets(data)
                return [scatter]
            return [scatter]
        return update

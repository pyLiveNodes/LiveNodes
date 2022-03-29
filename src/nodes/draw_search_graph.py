import collections
import numpy as np

from .node import Node

import time
from itertools import groupby
import seaborn as sns

import multiprocessing as mp



class Draw_search_graph(Node):
    channels_in = ['HMM Meta', 'Hypothesis']
    channels_out = []

    category = "Draw"
    description = "" 

    example_init = {
        "n_hypos": 3, 
        "name": "Search Graph",
    }

    def __init__(self, n_hypos = 3, name = "Search Graph", **kwargs):
        super().__init__(name=name, **kwargs)

        # process
        self.name = name
        
        self.hmm_meta = None

        # renderer
        self.graph = None
        self.topology = None

        self._axes_setup = False
        self.n_hypos = n_hypos

        self.bar_objs = []
        self.labels = []
        self.previous_alphas = []
        self.token_node_map = {}


    def _settings(self):
        return {\
            "name": self.name,
            "n_hypos": self.n_hypos
           }

    def _hack_get_atom_from_model_id(self, model_id):
        return '-'.join(model_id.split('-')[:-1])

    def _setup_axes(self, subfig):
        self.axes = subfig.subplots(len(self.tokens), 1)
        if len(self.tokens) == 1:
            self.axes = [self.axes]

        self.token_node_map = {token: list(sorted([(int(key), node["model_name"]) # lets hope that the nodeIds are sorted... as this is very hacky atm
                    for key, node in self.graph['nodes'].items() if node["model_name"].startswith(f'{token}_')])) # lets hope, that the <token>_<atom>-<stateId> convention holds...
                for token in self.tokens}

        # hack: assume model_name = <atom_name>-<state> -> then we can just use split 
        token_sub_colors = {token: [self.atom_colors[self._hack_get_atom_from_model_id(atom[1])] for atom in self.token_node_map[token]] for token in self.tokens}

        for ax, token in zip(self.axes, self.tokens):
            ax.set_ylim(0, 1)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)

            n_atoms = len(self.token_node_map[token])
            ax.set_xlim(0, n_atoms)
            self.labels.append(ax.text(0.005, 0.95, token, zorder=100, c="white", fontproperties=ax.xaxis.label.get_font_properties(), rotation='horizontal', va='top', ha='left', transform = ax.transAxes))
            # ax.set_ylabel(token, rotation=0, ha='right', va='center')

            self.previous_alphas.append([1] * n_atoms)
            verts = [(start, 1) for start in range(n_atoms)]
            self.bar_objs.append(ax.broken_barh(verts, yrange=(0, 1), facecolors=token_sub_colors[token]))

    def _empty_queue(self, queue):
        res = None
        while not queue.empty():
            res = queue.get()
        return res


    def init_draw(self, subfig):
        subfig.suptitle("Search Graph", fontsize=14)
        
        def update (hypothesis, hmm_meta):
            nonlocal self, subfig
    
            alpha_val = 0.5

            meta = self._empty_queue(self.queue_meta)
            hypo = self._empty_queue(self.queue_hypo)

            # TODO: allow for this to change even if axes is already setup
            if hmm_meta is not None and not self._axes_setup:
                self.graph = meta.get('search_graph')
                self.topology = meta.get('topology')
                self.tokens = list(self.topology.keys())

                self.token_colors, self.atom_colors, self.state_colors = self._init_colors(self.topology)

                self._setup_axes(subfig)
                self._axes_setup = True
                # return self.labels
            
            # print('Update', self._axes_setup, self.graph is not None)
            
            if self._axes_setup and hypothesis is not None:
                state_ids = hypothesis[:self.n_hypos]

                res_changed_bars = [] # faster if only few bars are changed, albeit less elegant than before
                for i, bar in enumerate(self.bar_objs):
                    alphas = [1 if x[0] in state_ids else alpha_val for x in self.token_node_map[self.tokens[i]]]
                    all_alphas = alphas + self.previous_alphas[i]
                    self.previous_alphas[i] = alphas
                    if sum(all_alphas) > len(all_alphas) * alpha_val: # if one alpha is higher than alpha_val this will return true
                        res_changed_bars.append(bar)
                        bar.set_alpha(alphas)

                # if np.random.random() > 0.95: # some events i am not entirely aware of result in bars being wiped out and not redrawn, as we do keep track of them
            return self.labels + self.bar_objs
                # return res_changed_bars
            # return []
        return update


    def _should_process(self, hypothesis=None, hmm_meta=None):
        return hypothesis is not None and \
            (self.hmm_meta is not None or hmm_meta is not None)

    def process(self, hypothesis, hmm_meta=None):
        if hmm_meta is not None:
            self.hmm_meta = hmm_meta

        self._emit_draw({'hypothesis': hypothesis, 'colors': self.hmm_meta})



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


import collections
import numpy as np

from .blit import BlitManager
from .node import Node

import time
from itertools import groupby
import seaborn as sns


def convert_pos(pos, yrange):
        ymin, ywidth = yrange
        ymax = ymin + ywidth
        verts = [[(xmin, ymin),
                (xmin, ymax),
                (xmin + xwidth, ymax),
                (xmin + xwidth, ymin),
                (xmin, ymin)] for xmin, xwidth in pos]
        return verts


# there is likeley a more efficient and elegant way with reduce here.
def convert_list_pos(itms, x_max, yrange):
    start = max(0, x_max-len(itms))
    pos = []
    names = []
    for act, group in groupby(itms):
        n_itms = len(list(group))
        next_start = start + n_itms
        pos.append((start, next_start))
        names.append(act)
        start = next_start
    # print(names[0], start, sum([y - x for x, y in pos]), len(itms), multiplier)
    return names, convert_pos(pos, yrange)



class Draw_recognition(Node):
    # TODO: consider removing the filter here and rather putting it into a filter node
    def __init__(self, xAxisLength=[50, 50, 50, 5000], name = "Recognition", dont_time = False):
        super().__init__(name=name, has_outputs=False, dont_time=dont_time)
        self.xAxisLength = xAxisLength

        self.verts = []
        self.names = []
    
    def _get_setup(self):
        return {\
            "name": self.name,
            "xAxisLength": self.xAxisLength
           }

    def init_draw(self, subfig):
        bar_names = ["State", "Atom", "Token", "Reference"]
        yrange = (0, 0.7)
        
        axes = subfig.subplots(len(bar_names), 1)
        subfig.suptitle(self.name, fontsize=14)

        bar_objs = []
        txt_fout_objs = [] 
        txt_fin_objs = []
        
        for ax, name, xmx in zip(axes, bar_names, self.xAxisLength):
            ax.set_ylim(0, 1)
            ax.set_xlim(0, xmx)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_ylabel(name)

            # many thanks to: https://stackoverflow.com/questions/59587466/how-can-i-annotate-a-grouped-broken-barh-chart-python-matplotlib
            bar_objs.append(ax.broken_barh([(0, 0)], yrange=yrange, edgecolor='white'))
            # bar_objs.append(ax.broken_barh([(0, 0)], yrange=yrange))
            txt_fout_objs.append(ax.text(x=0, y=0.9, s="", ha='left', va='top', 
                color='black', fontsize=12)) #backgroundcolor='grey',
            txt_fin_objs.append(ax.text(x=xmx, y=0.9, s="", ha='right', va='top', 
                color='black', fontsize=12)) #backgroundcolor='grey',

        # Add legend
        # handles = [ mpatches.Patch(color=val, label=key) for key, val in self.token_cols.items()]
        # legend = subfig.legend(handles=handles, loc='upper right')
        # legend.set_alpha(0) # TODO: for some reason the legend is transparent, no matter what i set here...
        # legend.set_zorder(100)

        def update (**kwargs):
            nonlocal self, bar_objs, txt_fout_objs, txt_fin_objs
            if len(self.verts) > 0:
                for bar_obj, tx_out, tx_in, verts, names, colors in zip(bar_objs, txt_fout_objs, txt_fin_objs, self.verts, self.names, self._bar_colors):
                    bar_obj.set_verts(verts)
                    bar_obj.set_facecolor([colors[name] for name in names])
                    tx_out.set_text(names[0])
                    tx_in.set_text(names[-1])
            return bar_objs + txt_fout_objs + txt_fin_objs
        return update


    def _init_colors(self, topology):
        c = sns.color_palette("deep", len(topology))
        _state_colors = dict(zip(range(5), ['#b9b9b9', '#777777', '#3b3b3b'])) # bold assumption, that there are never more than 3 states
        _token_colors = dict(zip(topology.keys(), c))
        _atom_colors = {}
        for token, color in _token_colors.items():
            token_model = np.unique(topology[token])
            brightness_mod = list(reversed(np.linspace(0.8, 0.2, len(token_model)))) # this way with len=1 we use 0.8 instead of 0.2
            for i, atom in enumerate(token_model):
                _atom_colors[atom] = tuple([cc * brightness_mod[i] for cc in color])
        return _token_colors, _atom_colors, _state_colors

    def receive_data(self, paths, meta, **kwargs):
        if not hasattr(self, "_token_colors"):
            topology = meta.get('topology')
            token_colors, atom_colors, state_colors = self._init_colors(topology)
            self._bar_colors = [state_colors,
                    atom_colors,
                    token_colors,
                    token_colors]


        states, atoms, tokens = zip(*paths[-self.xAxisLength[0]:])

        state_names, state_verts = convert_list_pos(states, self.xAxisLength[0], (0, 0.7))
        atom_names, atom_verts = convert_list_pos(atoms, self.xAxisLength[1], (0, 0.7))
        token_names, token_verts = convert_list_pos(tokens, self.xAxisLength[2], (0, 0.7))
        ref_names, ref_verts = convert_list_pos(tokens, self.xAxisLength[2], (0, 0.7)) # TODO: this is clearly wrong :D

        self.verts = [state_verts, atom_verts, token_verts, ref_verts]
        self.names = [state_names, atom_names, token_names, ref_names]

import numpy as np

from .node import View

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



class Draw_recognition(View):
    channels_in = ['Recognition', 'Annotation', 'HMM Meta']
    channels_out = []

    category = "Draw"
    description = "" 

    example_init = {
        "name": "Recognition",
        "xAxisLength": [50, 50, 50, 5000]
    }

    def __init__(self, xAxisLength=[50, 50, 50, 5000], name = "Recognition", **kwargs):
        super().__init__(name=name, **kwargs)

        # process side
        self.colors = None

        # render side
        self._bar_colors = []

        self.xAxisLength = xAxisLength

        self.verts = [[], [], [], []]
        self.names = [[''], [''], [''], ['']]


    def _settings(self):
        return {\
            "name": self.name,
            "xAxisLength": self.xAxisLength
           }

    def _should_draw(self, **cur_state):
        # if not bool(cur_state):
        #     print('Draw infos', "recognition" in cur_state, "annotation" in cur_state, "colors" in cur_state, bool(cur_state))
        return bool(cur_state)

    def _init_draw(self, subfig):
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


        def update (recognition, annotation, colors):
            nonlocal self, bar_objs, txt_fout_objs, txt_fin_objs

            if colors is not None:
                self._bar_colors = colors


            states, atoms, tokens = zip(*recognition)

            self.names[0], self.verts[0] = convert_list_pos(states[-self.xAxisLength[0]:], self.xAxisLength[0], (0, 0.7))
            self.names[1], self.verts[1] = convert_list_pos(atoms[-self.xAxisLength[1]:], self.xAxisLength[1], (0, 0.7))
            self.names[2], self.verts[2] = convert_list_pos(tokens[-self.xAxisLength[2]:], self.xAxisLength[2], (0, 0.7))

            if annotation is not None:
                self.names[3], self.verts[3] = convert_list_pos(annotation[-self.xAxisLength[3]:], self.xAxisLength[3], (0, 0.7))

            #TODO: rework this to work properly with missing streams...
            # if len(self.verts) > 0 and len(self._bar_colors) > 0:
            for bar_obj, tx_out, tx_in, verts, names, colors in zip(bar_objs, txt_fout_objs, txt_fin_objs, self.verts, self.names, self._bar_colors):
                bar_obj.set_verts(verts)
                bar_obj.set_facecolor([colors[name] for name in names])
                tx_out.set_text(names[0])
                tx_in.set_text(names[-1])
            return bar_objs + txt_fout_objs + txt_fin_objs

        return update


    def _should_process(self, recognition=None, hmm_meta=None, annotation=None):

        res = recognition is not None \
            and (self.colors is not None or hmm_meta is not None) \
            and (annotation is not None or not self._is_input_connected('Annotation'))
        # if not res:
        #     print(recognition is not None, annotation is not None)
        return res
            # if the annotation input is connected it must be present for processing

    def process(self, recognition=None, hmm_meta=None, annotation=None, **kwargs):
        if hmm_meta is not None:
            token_colors, atom_colors, state_colors = self._init_colors(hmm_meta.get('topology'))
            self.colors = [state_colors, atom_colors, token_colors, token_colors]

        if len(recognition) > 0:
            # for the annotaiton, we'll assume it is in the normal (batch/file, time, channel) format and that batch is not relevant here
            # similarly we expect recognition not to have taken batch into account (ah fu... there is still some trouble there, that is not a true assumption)
            # print(np.array(annotation).shape, len(recognition))
            if annotation is not None:
                annotation = np.array(annotation)[0,:,0]
            self._emit_draw(recognition=recognition, colors=self.colors, annotation=annotation)
            # self._emit_draw(recognition=recognition, colors=self.colors, annotation=None)


    # TODO: move this to utils or something...
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

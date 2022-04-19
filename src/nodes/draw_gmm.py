import numpy as np
import seaborn as sns
import matplotlib as mpl

from .draw_scatter import Draw_scatter


class Draw_gmm(Draw_scatter):
    """
    Draw Gaussian Mixtures in two dimensional space along with the current data points as scatter plot.

    The gaussians are pre-rendered once received. The weight of each gaussian is represented as alpha values.

    The scatter drawing is passed of to draw_scatter.

    TODO: at the moment this includes it's own filter, as previously the biokit recognizer did only send the gaussians in full dimension.
    Now that a filter can be put in between, this class should be simplified.

    Draws on a matplotlib canvas.
    """

    channels_in = [
        "Data", "Channel Names", "HMM Meta", "Hypo States"
    ]  #"GMM Models", "GMM Means", "GMM Covariances", "GMM Weights"]
    channels_out = []

    category = "Draw"
    description = ""

    example_init = {
        "name": "GMM",
        "plot_names": ["Channel 1", "Channel 2"],
        "n_mixtures": 2,
        "n_scatter_points": 10,
        "name": "GMM",
        "ylim": (-1.1, 1.1)
    }

    # TODO: remove the plot_names filter! this should just be a step in the pipeline
    # (this entails fixing the gmms not being passed in the hmm meta stream but a stream of their own)

    def __init__(self,
                 plot_names,
                 n_mixtures=2,
                 n_scatter_points=50,
                 ylim=(-1.1, 1.1),
                 name="Draw Output Scatter",
                 **kwargs):
        super().__init__(n_scatter_points, ylim, name, **kwargs)

        self.graph = None
        self.topology = None

        self.plot_names = plot_names
        self.idx = None
        self.n_mixtures = n_mixtures
        self.update_scatter_fn = None
        self.model_ell_map = None
        self.ells_list = None

        self.bar_objs = []
        self.previous_alphas = []
        self.token_node_map = {}

        self.atom_colors = None
        self.gmms = None

    def _settings(self):
        return dict(
            {
                "plot_names": self.plot_names,
                "n_mixtures": self.n_mixtures
            },
            **super()._settings())

    def _init_draw(self, subfig):
        super_update = super()._init_draw(subfig)

        self.ax.set_xlabel(self.plot_names[0])
        self.ax.set_ylabel(self.plot_names[1])

        def update(data, atom_colors, gmms, hypo_states, channel_names):
            nonlocal self, subfig, super_update

            # only read the meta and prew_draw the gmms if we have created the idx (which we need the channel names for)

            # TODO: THIS is a problem!
            # We can never be sure these are all set at the same time, as the queue filling and matplotlib render are completely independent processes
            # yes, in the fill part the calls are basically syncronus, but the render process can still be called in between the queues!
            # gmm_models = self._empty_queue(self.queue_gmm_models)
            # gmm_means = self._empty_queue(self.queue_gmm_means)
            # gmm_covs = self._empty_queue(self.queue_gmm_covs)
            # gmm_weights = self._empty_queue(self.queue_gmm_weights)
            # gmms = self._empty_queue(self.queue_gmms) # TODO: consider separate stream for this (pro: can use filter, and can visualize training, con: complicated)

            if self.idx is None:
                # yes, we need this twice, this here is on the plotting process
                self.idx = [channel_names.index(x) for x in self.plot_names]

            if gmms is not None and self.ells_list is None:
                self.model_ell_map = {
                    model_name:
                    self._pre_draw_gmm(self.ax, model_name, m["means"],
                                       m["covariances"], m["mixture_weights"],
                                       atom_colors)
                    for model_name, m in gmms.items()
                }
                self.ells_list = list(
                    np.concatenate(list(self.model_ell_map.values()), axis=0))

            if hypo_states is not None and len(
                    hypo_states) > 0 and self.model_ell_map is not None:
                for model_name, ells in self.model_ell_map.items():
                    if model_name in hypo_states[:self.n_mixtures]:
                        for ell in ells:
                            ell.set_visible(True)
                            # ell.set_color(self.order_colors[hypo_states.index(model_name)])
                    else:
                        for ell in ells:
                            ell.set_visible(False)

            return self.ells_list + super_update(data=data,
                                                 channel_names=channel_names)

        return update

    def _should_process(self,
                        data=None,
                        channel_names=None,
                        hmm_meta=None,
                        hypo_states=None):
        return (data is not None) \
            and (hypo_states is not None) \
            and (self.channel_names is not None or channel_names is not None) \
            and (self.atom_colors is not None or hmm_meta is not None) \

    def process(self,
                data,
                hypo_states,
                channel_names=None,
                hmm_meta=None,
                **kwargs):
        if channel_names is not None:
            self.channel_names = channel_names

            # yes, we need this twice, this here is on the processing process
            self.idx = [channel_names.index(x) for x in self.plot_names]

        if hmm_meta is not None:
            _, self.atom_colors, _ = self._init_colors(hmm_meta["topology"])
            self.gmms = hmm_meta.get('gmms')

        # as data is (batch/file, time, channel)
        d = np.vstack(np.array(data)[:, :, self.idx])

        self.data = np.roll(self.data, d.shape[0], axis=0)
        self.data[:d.shape[0]] = d

        self._emit_draw(data=self.data[:self.n_scatter_points],
                        atom_colors=self.atom_colors,
                        gmms=self.gmms,
                        hypo_states=hypo_states,
                        channel_names=self.channel_names)

    # TODO: share these between the different hmm draws...
    def _init_colors(self, topology):
        c = sns.color_palette("deep", len(topology))
        _state_colors = dict(zip(
            range(3),
            ['#b9b9b9', '#777777', '#3b3b3b'
             ]))  # bold assumption, that there are never more than 3 states
        _token_colors = dict(zip(topology.keys(), c))
        _atom_colors = {}
        for token, color in _token_colors.items():
            token_model = np.unique(topology[token])
            brightness_mod = list(
                reversed(np.linspace(0.8, 0.2, len(token_model)))
            )  # this way with len=1 we use 0.8 instead of 0.2
            for i, atom in enumerate(token_model):
                _atom_colors[atom] = tuple(
                    [cc * brightness_mod[i] for cc in color])

        # To be save if a stream is missing, although likely more will break in that case.
        if '' not in _state_colors: _state_colors[''] = '#b9b9b9'
        if '' not in _token_colors: _token_colors[''] = '#b9b9b9'
        if '' not in _atom_colors: _atom_colors[''] = '#b9b9b9'

        return _token_colors, _atom_colors, _state_colors

    def _hack_get_atom_from_model_id(self, model_id):
        return '-'.join(model_id.split('-')[:-1])

    def _pre_draw_gmm(self, ax, model_id, means, covariance, mixture_weights,
                      atom_colors):
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

            ell = mpl.patches.Ellipse(
                means[i][self.idx],
                v[0],
                v[1],
                180 + angle,
                color=atom_colors[self._hack_get_atom_from_model_id(model_id)])
            ell.set_label(model_id)
            ell.set_zorder(1)
            ell.set_alpha(mixture_weights[i])
            ell.set_clip_box(ax.bbox)

            ell.set_visible(False)
            ax.add_patch(ell)
            ells.append(ell)
        return ells

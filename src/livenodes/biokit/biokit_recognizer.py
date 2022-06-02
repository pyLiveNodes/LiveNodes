from livenodes.core.node import Node
from livenodes.biokit.biokit import recognizer
import livenodes.biokit.utils as biokit_utils

import json

# TODO: figure out if needed (!) how we can train this as well...

from . import local_registry


@local_registry.register
class Biokit_recognizer(Node):
    """
    Hidden Markov Model Recognizer (for a BioKIT Feature Sequence Stream)

    Updates it's own recognition with each new batch of data and sends.
    Also sends the most likely hypothesis of the current state.

    Requires a pre-trained model (look at biokit_train.py)
    Requires a BioKIT Feature Sequence Stream
    """

    channels_in = ['Data', 'File', 'Reload']
    channels_out = ['Recognition', 'HMM Meta', 'Hypothesis', 'Hypo States']

    category = "BioKIT"
    description = ""

    example_init = {
        'name': 'Recognizer',
        'model_path': './models/',
        'token_insertion_penalty': 0
    }

    def __init__(self,
                 model_path,
                 token_insertion_penalty,
                 name="Recognizer",
                 **kwargs):
        super().__init__(name, **kwargs)

        self.model_path = model_path
        self.token_insertion_penalty = token_insertion_penalty

        self._load_recognizer()
        self.file = None

    def _load_recognizer(self):
        self.info('Loading Recognizer')
        with biokit_utils.model_lock(self.model_path):
            self.reco = recognizer.Recognizer.createNewFromFile(
                self.model_path, sequenceRecognition=True)
            # self.reco.limitSearchGraph(self.recognize_atoms) # TODO: enable this
            self.reco.setTokenInsertionPenalty(self.token_insertion_penalty)
            self.topology = self._get_topology()
            self._initial = True
            self.info('Recognizer loaded')

    def _settings(self):
        return {\
            # "batch": self.batch,
            "token_insertion_penalty": self.token_insertion_penalty,
            "model_path": self.model_path
        }

    def _should_process(self, data=None, file=None, reload=None):
        return data is not None \
            and (reload in [0, 1] or not self._is_input_connected('Reload')) \
            and (file is not None or not self._is_input_connected('File'))

    def process(self, data, file=None, reload=None, **kwargs):
        if reload and not self._initial:
            self._load_recognizer()

        # IMPORTANT/TODO: check if this is equivalent to the previous behaviour,ie if we always receive the file together with the data
        # file is optional, if it is not passed (ie None) it doesn't change except in the first send
        if file is not None:
            file = file[0][0][0]
            self._initial = self.file != file
            self.file = file

        am = self.reco.getAtomManager()
        dc = self.reco.getDictionary()

        for batch in data:
            _, path, _ = self.reco.decode(
                batch, generatepath=True, initialize=bool(self._initial)
            )  # not sure if we need to initialize this on the first call?

            if self._initial:
                # if file is not hooked up, we should set this to false at least
                self._initial = False

                # get search graph
                graph_json = self.reco.getSearchGraph().createGraphJson(
                    self.reco.getDictionary(), False)
                graph = json.loads(graph_json)

                # get gaussians
                gmm_models = []
                gmm_means = []
                gmm_cov = []
                gmm_weights = []
                gmms = {}
                for model_name in self.reco.getGaussMixturesSet(
                ).getAvailableModelNames():
                    gmm_id = self.reco.getGaussMixturesSet().getModelId(
                        model_name)
                    gmm_container = self.reco.getGaussMixturesSet(
                    ).getGaussMixture(gmm_id)
                    gmm = gmm_container.getGaussianContainer()
                    means = gmm.getMeanVectors()
                    mixture_weights = gmm_container.getMixtureWeights()
                    n_gaussians = len(means)
                    gmm_models.extend([model_name] * n_gaussians)
                    gmm_means.extend(means)
                    gmm_cov.extend([
                        gmm.getCovariance(i).getData()
                        for i in range(len(means))
                    ])
                    gmm_weights.extend(mixture_weights)

                    gmms[model_name] = {
                        "means":
                        means,
                        "mixture_weights":
                        mixture_weights,
                        "covariances": [
                            gmm.getCovariance(i).getData()
                            for i in range(len(means))
                        ]
                    }

                # send meta data
                self._emit_data(
                    {
                        "topology": self.topology,
                        "search_graph": graph,
                        'gmms': gmms
                    },
                    channel="HMM Meta")
                self._emit_data(gmm_models, channel="GMM Models")
                self._emit_data(gmm_means, channel="GMM Means")
                self._emit_data(gmm_cov, channel="GMM Covariances")
                self._emit_data(gmm_weights, channel="GMM Weights")

            self.info(
                f'Found path? {path != None} of length: {"" if path == None else len(path)}; was initial? {self._initial}'
            )

            res = []
            hypothesis = []
            hypo_states = []

            if path != None:
                res = [( \
                        r.mStateId,
                        am.getAtom(r.mAtomId).getName(),
                        dc.getToken(r.mTokenId)
                    ) for r in path]
                hypothesis = self.reco.handler.getCurrentHypoNodeIds()
                hypo_states = self.reco.handler.getCurrentHypoStates()

            # We will be proactive and tell subsequent nodes if we failed, rather than ommiting data (as this would break the clock approach)
            self._emit_data(res, channel="Recognition")

            # Maybe consider adding a mechanism that only calcs/gets this if someone requested it?
            # TODO: check this again and see if we can merge the streams somehow...
            self._emit_data(hypothesis, channel="Hypothesis")
            self._emit_data(hypo_states, channel="Hypo States")

    def _get_topology(self):
        dc = self.reco.getDictionary()
        am = self.reco.getAtomManager()

        # there is probably an easier way to get this...
        tokens = dc.getTokenList()
        topology = {}
        for token in tokens:
            atom_ids = dc.getDictionaryEntry(
                dc.getBaseFormId(token)).getAtomIdList()
            topology[token] = [
                am.getAtom(atomId).getName() for atomId in atom_ids
            ]
        return topology

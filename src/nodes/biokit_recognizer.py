import numpy as np
from .node import Node

from .biokit import recognizer

import seaborn as sns

import json

# TODO: figure out if needed (!) how we can train this as well...

class Biokit_recognizer(Node):
    channels_in = ['Data', 'File']
    channels_out = ['Recognition', 'HMM Meta', 'Hypothesis']

    category = "BioKIT"
    description = "" 

    example_init = {'name': 'Recognizer', 'model_path': './models/', 'token_insertion_penalty': 0}

    def __init__(self, model_path, token_insertion_penalty, name="Recognizer", **kwargs):
        super().__init__(name, **kwargs)

        self.model_path = model_path
        self.token_insertion_penalty = token_insertion_penalty

        self.reco = recognizer.Recognizer.createNewFromFile(self.model_path, sequenceRecognition=True)
        # self.reco.limitSearchGraph(self.recognize_atoms) # TODO: enable this
        self.reco.setTokenInsertionPenalty(self.token_insertion_penalty)

        self.topology = self._get_topology()

        self._initial = True
        self.file = -1

    def _settings(self):
        return {\
            # "batch": self.batch,
            "token_insertion_penalty": self.token_insertion_penalty,
            "model_path": self.model_path
        }

    def _should_process(self, data=None, file=None):
        return data is not None

    def process(self, data, file=None):
        # IMPORTANT/TODO: check if this is equivalent to the previous behaviour,ie if we always receive the file together with the data
        # file is optional, if it is not passed (ie None) it doesn't change except in the first send
        self._initial = self.file != file
        self.file = file

        am = self.reco.getAtomManager()
        dc = self.reco.getDictionary()

        _, path, _ = self.reco.decode(data, generatepath=True, initialize=self._initial) # not sure if we need to initialize this on the first call?

        if self._initial:
            # get search graph
            graph_json = self.reco.getSearchGraph().createGraphJson(self.reco.getDictionary(), False)
            graph = json.loads(graph_json)

            # get gaussians
            gmm_models = []
            gmm_means = []
            gmm_cov = []
            gmm_weights = []
            gmms = {}
            for model_name in self.reco.getGaussMixturesSet().getAvailableModelNames():
                gmm_id = self.reco.getGaussMixturesSet().getModelId(model_name)
                gmm_container = self.reco.getGaussMixturesSet().getGaussMixture(gmm_id)
                gmm = gmm_container.getGaussianContainer()
                means = gmm.getMeanVectors()
                mixture_weights = gmm_container.getMixtureWeights()
                n_gaussians = len(means)
                gmm_models.extend([model_name] * n_gaussians)
                gmm_means.extend(means)
                gmm_cov.extend([gmm.getCovariance(i).getData() for i in range(len(means))])
                gmm_weights.extend(mixture_weights)

                gmms[model_name] = {
                    "means": means,
                    "mixture_weights": mixture_weights,
                    "covariances": [gmm.getCovariance(i).getData() for i in range(len(means))]
                }

            # send meta data
            self._emit_data({"topology": self.topology, "search_graph": graph, 'gmms': gmms}, channel="HMM Meta") 
            self._emit_data(gmm_models, channel="GMM Models")
            self._emit_data(gmm_means, channel="GMM Means")
            self._emit_data(gmm_cov, channel="GMM Covariances")
            self._emit_data(gmm_weights, channel="GMM Weights")
            
        if path != None:
            self.info('Found path!')
            res = [( \
                    r.mStateId, 
                    am.getAtom(r.mAtomId).getName(),
                    dc.getToken(r.mTokenId)
                ) for r in path]
            # print(res)
            self._emit_data(res, channel="Recognition")

            # Maybe consider adding a mechanism that only calcs/gets this if someone requested it?
            # TODO: check this again and see if we can merge the streams somehow...
            self._emit_data(self.reco.handler.getCurrentHypoNodeIds(), channel="Hypothesis")
            self._emit_data(self.reco.handler.getCurrentHypoStates(), channel="Hypo States")

    def _get_topology(self):
        dc = self.reco.getDictionary()
        am = self.reco.getAtomManager() 

        # there is probably an easier way to get this...
        tokens = dc.getTokenList()
        topology = {}
        for token in tokens:
            atom_ids = dc.getDictionaryEntry(dc.getBaseFormId(token)).getAtomIdList()
            topology[token] = [am.getAtom(atomId).getName() for atomId in atom_ids]
        return topology
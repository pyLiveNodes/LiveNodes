import numpy as np
from .node import Node

from .biokit import recognizer

import seaborn as sns

import json

# TODO: figure out if needed (!) how we can train this as well...

class Biokit_recognizer(Node):
    def __init__(self, model_path, token_insertion_penalty, name="Recognizer", dont_time=False):
        super().__init__(name, dont_time)

        self.model_path = model_path
        self.token_insertion_penalty = token_insertion_penalty

        self.reco = recognizer.Recognizer.createNewFromFile(self.model_path, sequenceRecognition=True)
        # self.reco.limitSearchGraph(self.recognize_atoms) # TODO: enable this
        self.reco.setTokenInsertionPenalty(self.token_insertion_penalty)

        self.topology = self._get_topology()

        self._initial = True
        self.file = None

    @staticmethod
    def info():
        return {
            "class": "Biokit_recognizer",
            "file": "biokit_recognizer.py",
            "in": ["Data", "File"],
            "out": ["Recognition", "HMM Meta", "Hypothesis"],
            "init": {
                "name": "Recognizer",
                "model_path": "./models/",
                "token_insertion_penalty": 0,
            },
            "category": "BioKIT"
        }
    
    @property
    def in_map(self):
        return {
            "Data": self.receive_data,
            "File": self.receive_file,
        }

    def _get_setup(self):
        return {\
            # "batch": self.batch,
            "token_insertion_penalty": self.token_insertion_penalty,
            "model_path": self.model_path
        }

    def receive_file(self, file, **kwargs):
        if self.file != file[0]:
            self._initial = True
            self.file = file[0]

    def receive_data(self, fs, **kwargs):
        am = self.reco.getAtomManager()
        dc = self.reco.getDictionary()

        _, path, _ = self.reco.decode(fs, generatepath=True, initialize=self._initial) # not sure if we need to initialize this on the first call?

        if self._initial:
            self._initial = False
            graph_json = self.reco.getSearchGraph().createGraphJson(self.reco.getDictionary(), False)
            graph = json.loads(graph_json)
            self.send_data({"topology": self.topology, "search_graph": graph}, data_stream="HMM Meta") 

        if path != None:
            res = [( \
                    r.mStateId, 
                    am.getAtom(r.mAtomId).getName(),
                    dc.getToken(r.mTokenId)
                ) for r in path]
            # print(res)
            self.send_data(res, data_stream="Recognition")

            # Maybe consider adding a mechanism that only calcs/gets this if someone requested it?
            self.send_data(self.reco.handler.getCurrentHypoNodeIds(), data_stream="Hypothesis")

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
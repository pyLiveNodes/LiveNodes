import numpy as np
from .node import Node

import recognizer

import seaborn as sns


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
    

    def _get_setup(self):
        return {\
            # "batch": self.batch,
            "token_insertion_penalty": self.token_insertion_penalty,
            "model_path": self.model_path
        }


    def receive_data(self, fs, **kwargs):
        am = self.reco.getAtomManager()
        dc = self.reco.getDictionary()

        _, path, _ = self.reco.decode(fs, generatepath=True, initialize=self._initial) # not sure if we need to initialize this on the first call?

        if self._initial:
            self._initial = False
            self.send_data({"topology": self.topology}, data_stream="Meta") 

        if path != None:
            res = [( \
                    r.mStateId, 
                    am.getAtom(r.mAtomId).getName(),
                    dc.getToken(r.mTokenId)
                ) for r in path]
            # print(res)
            self.send_data(res) 


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
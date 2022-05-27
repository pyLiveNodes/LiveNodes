from itertools import groupby
import json
import time
from typing import DefaultDict
import os
import traceback
import numpy as np
from filelock import FileLock

import livenodes.biokit.utils as biokit_utils
from livenodes.core.node import Node, Location
from livenodes.biokit.biokit import BioKIT, logger, recognizer

from . import local_registry


# TODO: figure out if/how we can update an already trained model with only the new data
# -> see notes: use learning rate that takes the number of samples into account of previous training
# TODO: also figure out how to adapt a model to the current wearer -> should be a standard procedure somewhere...
# -> have a second look at the MAP tests in biokit
@local_registry.register
class Biokit_update_model(Node):
    """
    Updates a Hidden Markov Model Recognizer (for a BioKIT Feature Sequence Stream)

    Reads a given model or creates a new one if none is found.
    Every x seconds the received data will be used to update the model.
    Once the pipeline stops, the new model is written out to files.

    If the collected data includes unseen activities a new target is created using the passed parameter of default phases.
    If the data includes seen activities they are currently discarded. This is a TODO point, where these should also be used for training.

    Requires a BioKIT Feature Sequence Stream
    """

    channels_in = ["Data", "Annotation", "Train"]
    channels_out = ["Training", "Text"]

    category = "BioKIT"
    description = ""

    example_init = {
        "name": "Train",
        "model_path": "./models/",
        "atomList": [],
        "tokenDictionary": {},
        "train_iterations": 5,
        "token_insertion_penalty": 0,
    }

    def __init__(self,
                 model_path,
                 phases_new_act,
                 token_insertion_penalty,
                 train_iterations,
                 catch_all="None",
                 name="Train",
                 **kwargs):
        super().__init__(name, **kwargs)

        if self.compute_on is Location.SAME:
            # TODO: double check if/why this may be the case
            raise ValueError(f'compute_on may not be same for {str(self)}.')

        self.model_path = model_path
        self.train_iterations = train_iterations
        self.phases_new_act = phases_new_act
        self.token_insertion_penalty = token_insertion_penalty
        self.catch_all = catch_all

        self.storage_annotation = []
        self.storage_data = []

        self.last_training = None
        self.last_msg = None

        self.reco = None

        self.currently_training = False

    def _settings(self):
        return {\
            # "batch": self.batch,
            "token_insertion_penalty": self.token_insertion_penalty,
            "model_path": self.model_path,
            "train_iterations": self.train_iterations,
            "phases_new_act": self.phases_new_act,
            "catch_all": self.catch_all,
        }

    def _add_atoms_to_topo(self, atomList, topologyInfo):
        ### As we currently cannot manipulate the topologyInfo (to be more precise the topoTree), we'll replace it
        # ie we'll copy all information from it and add the new stuff on top, then return the new topologyInfo
        # topoTree = topologyInfo.getTopoTree()

        n_topologyInfo = BioKIT.TopologyInfo()
        n_topoTree = n_topologyInfo.getTopoTree()

        ### Create Topologies
        # add old topologies into new topology info
        print(topologyInfo.getTopologies().keys())
        for atom, topology in topologyInfo.getTopologies().items():
            n_topologyInfo.addTopology(atom, topology.getRootNodes(),
                                       topology.getTransitions(),
                                       topology.getInitialStates(),
                                       topology.getOutgoingTransitions())
        # add the new topologies
        print(atomList)
        for atom in atomList:
            rootNodes = []
            transitions = []
            states = atomList[atom]
            #if the token only has 1 state, then there is only the outgoing
            #transition
            if (len(states) == 1):
                rootNodes = ['ROOT-' + states[0]]
                transitions = []
                initialStates = [0]
                transitions.append(BioKIT.Transition(0, 0, 0.7))
                outgoingTransitions = [(0, 0.7)]
                n_topologyInfo.addTopology(atom, rootNodes, transitions,
                                           initialStates, outgoingTransitions)
            #else every state (except the last one) points to itself
            #and the next state
            else:
                for index, name in enumerate(states):
                    rootNodes.append('ROOT-' + name)
                    transitions.append(BioKIT.Transition(index, index, 0.7))
                    if index != len(states) - 1:
                        transitions.append(
                            BioKIT.Transition(index, index + 1, 0.7))

            initialStates = [0]
            outgoingTransitions = [(len(states) - 1, 0.7)]
            n_topologyInfo.addTopology(atom, rootNodes, transitions,
                                       initialStates, outgoingTransitions)

        ### Rebuild topoTree
        # Notes: i would prefer we just append the new tree nodes, but we canno access the old ones, so we wil for now just re-create the whole thing
        topos = list(n_topologyInfo.getTopologies().keys())

        # n_nodes = topoTree.countNodes() + 1 # this will result in non-consequtive root-i as countNodes > len(rootNodes), but if there is no assumption for them to be consequtive we should be fine...
        # newNode = topoTree.getRootNodes()[-1] # This would be the cleaner way, but is currently not supported by biokit
        # newNode = BioKIT.TopoTreeNode('ROOT-' + str(n_nodes))
        newNode = BioKIT.TopoTreeNode('ROOT-0')
        n_topoTree.addRootNode(newNode)
        for i, atom in enumerate(topos):
            i += 1
            if (i <= len(topos) - 1):
                rootNode = newNode
                rootNode.setQuestions('0=' + atom)
                rootNode.setChildNode(True, BioKIT.TopoTreeNode(atom, atom))
                newNode = BioKIT.TopoTreeNode('ROOT-' + str(i))
                rootNode.setChildNode(False, newNode)
            else:
                rootNode.setChildNode(False, BioKIT.TopoTreeNode(atom, atom))

        n_topoTree.createDotGraph('topo.dot')
        return n_topologyInfo

    def _add_token(self, token, atoms, featuredimensionality, nrofmixtures):
        atomManager = self.reco.getAtomManager()
        dictionary = self.reco.getDictionary()

        atomList = {}
        for atom in atoms:
            atomList[atom] = ["0"]
            atomManager.addAtom(atom, ["atoms"], True)
        dictionary.addToken(token, atoms)

        if type(nrofmixtures) == int:
            tmpdict = {}
            for atom in atomList:
                tmpdict[atom] = nrofmixtures
            nrofmixtures = tmpdict

        for atom in nrofmixtures:
            if type(nrofmixtures[atom]) == int:
                tmplist = len(atomList[atom]) * [
                    nrofmixtures[atom],
                ]
                nrofmixtures[atom] = tmplist

        topologyInfo = self._add_atoms_to_topo(
            atomList, self.reco.modelMapper.getTopologyInfo())

        # now start adding tokens and atoms
        for atom in sorted(atomList):
            recognizer.Recognizer.addModel(atom, atomList[atom],
                                           nrofmixtures[atom],
                                           featuredimensionality,
                                           self.reco.gaussianContainerSet,
                                           self.reco.gaussMixturesSet,
                                           self.reco.mixtureTree)

        tsm = BioKIT.ZeroGram(dictionary)

        #create the Recognizer and return it
        return recognizer.Recognizer(self.reco.gaussianContainerSet,
                                     self.reco.gaussMixturesSet,
                                     dictionary.getAtomManager(),
                                     self.reco.mixtureTree,
                                     topologyInfo,
                                     dictionary,
                                     tsm,
                                     initSearchGraph=True)

    def _train(self):
        # we should never ever change the self.storage data as this will make everything out of sync!
        # ie if len(data) = 10 and len(annotation) = 9 (and 1 is in queue to be added) then we remove the last data, but the queue will still be added.
        #   -> every new label is shifted by 1 package. this propagates until nothing fits to nothing anymore
        # Note: this is a very unlikely scenario due to the clock mechanism, but still.
        storage_data = self.storage_data
        storage_annotation = self.storage_annotation

        len_d, len_a = len(storage_data), len(storage_annotation)
        keep = min(len_d, len_a)
        if len_d != len_a:
            logger.warn(
                f"Data length ({len_d}) did not match annotation length ({len_a})"
            )
            storage_data = storage_data[:keep]
            storage_annotation = storage_annotation[:keep]

        if len(storage_data) <= 0:
            return

        featuredimensionality = len(storage_data[0][0])

        ### Create Recognizer instance
        is_new = not os.path.exists(self.model_path)
        if not is_new:
            print('Adding new activities to existing model')
            self.reco = recognizer.Recognizer.createNewFromFile(
                self.model_path, sequenceRecognition=True)
        else:
            print('Adding new activities to new model')
            print('Feature dim:', len(storage_data[0][0]))
            # This is kinda ugly, but biokit does not allow empty dicts here :/
            self.reco = recognizer.Recognizer.createCompletelyNew(
                {
                    f"{self.catch_all}_1": ["0"],
                }, {self.catch_all: [f"{self.catch_all}_1"]},
                1,
                featuredimensionality=featuredimensionality)
            # self.reco = recognizer.Recognizer.createCompletelyNew({}, {}, 1, featuredimensionality=featuredimensionality)
        self.reco.setTokenInsertionPenalty(self.token_insertion_penalty)

        ### Prepare Data
        tokens = []
        data = []

        # TODO: clean this up and make sure we don't need store the data twice (once on self and once in fs)
        n_groups = len(list(groupby(storage_annotation)))
        grouped_tokens = groupby(zip(storage_annotation,
                                    storage_data),
                                key=lambda x: x[0])
        for i, (token, g) in enumerate(grouped_tokens):
            if i < n_groups - 1:
                pro_sq = BioKIT.FeatureSequence()
                for x in g:
                    pro_sq.append(x[1])  # accumulate
                tokens.append(token)
                data.append(pro_sq)
            else:
                print("Skipped last group, as its not finished yet", n_groups,
                      i)

        ### remove known tokens from processed list (they are already trained, and will atm not be updated, see future work)
        known_tokens = self.reco.getDictionary().getTokenList()
        if is_new:
            # catch all is not known (ie not trained) if the recognizer is new (it had to be added in init, as biokit throws an error otherwise)
            known_tokens.remove(self.catch_all)

        stored_tokens = np.unique(tokens)
        # add new tokens (except catch_all )
        for token in stored_tokens:
            if token != self.catch_all and not token in known_tokens:
                self.reco = self._add_token(
                    token,
                    [f"{token}_{i}" for i in range(self.phases_new_act)],
                    featuredimensionality=featuredimensionality,
                    nrofmixtures=1)

        # decide which tokens to train
        tokens = np.array(tokens, dtype=object)
        data = np.array(data, dtype=object)

        available_samples = biokit_utils.calc_samples_per_token(np.expand_dims(tokens, axis=-1), data)
        if is_new or not os.path.exists(f'{self.model_path}/train_samples.json'):
            trained_samples = DefaultDict(int)
        else:
            with open(f'{self.model_path}/train_samples.json', 'r') as f:
                trained_samples = json.load(f)

        self.debug(trained_samples, available_samples)
        # keep tokens that are not in known_tokens unless the stored data is more than the trained data
        keep_tokens = list(filter(lambda x: (not x in known_tokens) or (available_samples.get(x, 0) > trained_samples.get(x, 0)), stored_tokens))
        idx = np.isin(tokens, keep_tokens)
        
        ### Train
        if len(tokens[idx]) == 0:
            self.info("No new activities")
            return
        
        self.info("Learning Tokens:", keep_tokens)

        biokit_utils.train_sequence(self.reco, iterations=self.train_iterations, seq_tokens=np.expand_dims(tokens[idx], axis=-1), seq_data=data[idx], model_path=self.model_path)


    def _should_process(self, data=None, annotation=None, train=None):
        return data is not None \
            and annotation is not None \
            and train in [0, 1] # train should be either 0 or 1, but not None

    def process(self, data, annotation, train, **kwargs):
        # TODO: make sure this is proper
        self.storage_data.extend(data)
        self.storage_annotation.extend(annotation)


        self.info(train, self.currently_training)
        if train and not self.currently_training:
            self.currently_training = True
            self._emit_data(1, channel="Training")
            
            try:
                with biokit_utils.model_lock(self.model_path):
                    print('Update!', len(self.storage_data))

                    self._emit_data(f"[{str(self)}]\n      Starting training.",
                                    channel="Text")
                    self._train()
                    self._emit_data(f"[{str(self)}]\n      Finished training.",
                                    channel="Text")

                    print('Trained model')
            except Exception as err:
                print(traceback.format_exc())
                print(err)
            self.currently_training = False
            time.sleep(1)
        else:
            self._emit_data(0, channel="Training")
            self._emit_data(f"[{str(self)}]\n      Waiting for instructions", channel="Text")


        # TODO: find a place to put this! -> some separate node probably
        # elif self.last_msg + 1 <= cur_time:
        #     self._emit_data(
        #         f"[{str(self)}]\n     Next training: {self.update_every_s - (self.last_msg - self.last_training):.2f}s.",
        #         channel="Text")
        #     self.last_msg = cur_time

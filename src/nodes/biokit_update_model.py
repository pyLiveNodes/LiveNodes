from itertools import groupby
from turtle import update
from typing import DefaultDict
import threading
import numpy as np
from .node import Node
from .biokit import BioKIT, logger, recognizer
import time

import multiprocessing as mp
import os
import traceback


# TODO: figure out if/how we can update an already trained model with only the new data
    # -> see notes: use learning rate that takes the number of samples into account of previous training
# TODO: also figure out how to adapt a model to the current wearer -> should be a standard procedure somewhere...
    # -> have a second look at the MAP tests in biokit
class Biokit_update_model(Node):
    channels_in = ["Data", "Annotation"]
    channels_out = ["Text"]

    category = "BioKIT"
    description = "" 

    example_init = {
        "name": "Train",
        "model_path": "./models/",
        "atomList": [],
        "tokenDictionary": {},
        "train_iterations": [5, 5],
        "token_insertion_penalty": 0,
    }

    def __init__(self, model_path, phases_new_act, token_insertion_penalty, train_iterations, catch_all="None", update_every_s=60, name="Train", **kwargs):
        super().__init__(name, **kwargs)

        self.model_path = model_path
        self.train_iterations = train_iterations
        self.phases_new_act = phases_new_act
        self.token_insertion_penalty = token_insertion_penalty
        self.update_every_s = update_every_s
        self.catch_all = catch_all

        self.storage_annotation = []
        self.storage_data = []

        self.last_training = time.time()
        self.last_msg = time.time()

    def _settings(self):
        return {\
            # "batch": self.batch,
            "token_insertion_penalty": self.token_insertion_penalty,
            "model_path": self.model_path,
            "train_iterations": self.train_iterations,
            "phases_new_act": self.phases_new_act,
            "update_every_s": self.update_every_s,
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
            n_topologyInfo.addTopology(
                atom,
                topology.getRootNodes(),
                topology.getTransitions(),
                topology.getInitialStates(),
                topology.getOutgoingTransitions()
            )
        # add the new topologies 
        print(atomList)
        for atom in atomList:
            rootNodes = []
            transitions = []
            states = atomList[atom]
            #if the token only has 1 state, then there is only the outgoing
            #transition
            if(len(states) == 1):
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
                rootNode.setChildNode(True,
                                        BioKIT.TopoTreeNode(atom, atom))
                newNode = BioKIT.TopoTreeNode('ROOT-' + str(i))
                rootNode.setChildNode(False, newNode)
            else:
                rootNode.setChildNode(False,
                                        BioKIT.TopoTreeNode(atom, atom))
        
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
                tmplist = len(atomList[atom]) * [nrofmixtures[atom], ]
                nrofmixtures[atom] = tmplist

        topologyInfo = self._add_atoms_to_topo(atomList, self.reco.modelMapper.getTopologyInfo())
        
        # now start adding tokens and atoms
        for atom in sorted(atomList):
            recognizer.Recognizer.addModel(atom, atomList[atom], nrofmixtures[atom],
                         featuredimensionality, self.reco.gaussianContainerSet,
                         self.reco.gaussMixturesSet, self.reco.mixtureTree)

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
        len_d, len_a = len(self.data), len(self.annotations)
        keep = min(len_d, len_a) 
        if len_d != len_a:
            logger.warn(f"Data length ({len_d}) did not match annotation length ({len_a})")
            self.data = self.data[:keep]
            self.annotations = self.annotations[:keep]

        if len(self.data) <= 0:
            return

        featuredimensionality = len(self.data[0][0])

        ### Create Recognizer instance
        is_new = not os.path.exists(self.model_path)
        if not is_new:
            print('Adding new activities to existing model')
            self.reco = recognizer.Recognizer.createNewFromFile(self.model_path, sequenceRecognition=True)
        else:
            print('Adding new activities to new model')
            print('Feature dim:', len(self.data[0][0]))
            # This is kinda ugly, but biokit does not allow empty dicts here :/
            self.reco = recognizer.Recognizer.createCompletelyNew({f"{self.catch_all}_1": ["0"], }, {self.catch_all: [f"{self.catch_all}_1"]}, 1, featuredimensionality=featuredimensionality)
            # self.reco = recognizer.Recognizer.createCompletelyNew({}, {}, 1, featuredimensionality=featuredimensionality)
        self.reco.setTokenInsertionPenalty(self.token_insertion_penalty)

        ### Prepare Data
        processedTokens = DefaultDict(list)

        # TODO: clean this up and make sure we don't need store the data twice (once on self and once in fs)
        n_groups = len(list(groupby(self.annotations)))
        grouped_atoms = groupby(zip(self.annotations, self.data), key=lambda x: x[0])
        for i, (atom, g) in enumerate(grouped_atoms):
            if i < n_groups - 1:
                pro_sq = BioKIT.FeatureSequence()
                for x in g: pro_sq.append(x[1]) # accumulate 
                processedTokens[atom].append(pro_sq)
            else:
                print("Skipped last group, as its not finished yet", n_groups, i)

        ### remove known tokens from processed list (they are already trained, and will atm not be updated, see future work)
        known_tokens = self.reco.getDictionary().getTokenList()

        for t in known_tokens:
            if t in processedTokens:
                if t != self.catch_all or not is_new:
                    del processedTokens[t]

        print("Now training:", processedTokens.keys())

        for token in processedTokens.keys():
            if token != self.catch_all:
                self.reco = self._add_token(token, [f"{token}_{i}" for i in range(self.phases_new_act)], featuredimensionality=featuredimensionality, nrofmixtures=1)


        ### Setup trainer
        self.reco.setTrainerType(recognizer.TrainerType('merge_and_split_trainer'))
        config = self.reco.trainer.getConfig()
        config.setSplitThreshold(500)
        config.setMergeThreshold(100)
        config.setKeepThreshold(10)
        config.setMaxGaussians(10)

        ### Train
        if len(processedTokens.keys()) == 0:
            print("No new activities")
            return


        logger.info('=== Initializaion ===')
        for atom in processedTokens:
            for trainingData in processedTokens[atom]:
                self.reco.storeTokenSequenceForInit(trainingData, [atom], fillerToken=-1, addFillerToBeginningAndEnd=False)
        self.reco.initializeStoredModels()


        logger.info('=== Train Tokens ===')
        # Use the fact that we know each tokens start and end
        for i in range(self.train_iterations[0]):
            logger.info(f'--- Iteration {i} ---')
            for atom in processedTokens:
                for trainingData in processedTokens[atom]:
                    # Says sequence, but is used for small chunks, so that the initial gmm training etc is optimized before we use the full sequences
                    self.reco.storeTokenSequenceForTrain(trainingData, [atom], fillerToken=-1, ignoreNoPathException=True, addFillerToBeginningAndEnd=False)
            self.reco.finishTrainIteration()


    def _should_process(self, data=None, annotation=None):
        return data is not None \
            and annotation is not None

    def _onstop(self):
        if self.reco is not None:
            # Save the model when stop_processing is called
            self.reco.saveToFiles(self.model_path)
            print('Saved recognizer to disk')
        else:
            print('No model was trained')

    def process(self, data, annotation):
        # TODO: make sure this is proper
        self.storage_data.extend(data)
        self.storage_annotation.extend(annotation)

        cur_time = time.time()
        if self.last_training + 60 >= cur_time:
            self.last_training = cur_time
            
            print('Update!', len(self.data))

            try:
                self._emit_data(f"[{str(self)}]\n      Starting training.", channel="Text") 
                self._train()
                self._emit_data(f"[{str(self)}]\n      Finished training.", channel="Text") 

                print('Trained model')
            except Exception as err:
                print(traceback.format_exc())
                print(err)

        elif self.last_msg + 1 >= cur_time:
            self._emit_data(f"[{str(self)}]\n     Next training: {self.update_every_s - (self.last_msg - self.last_training):.2f}s.", channel="Text") 



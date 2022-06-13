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


def element_wise_diff(arr):
    w = np.array(arr, dtype=object)
    return np.concatenate([[False], w[1:] != w[:-1]], axis=0).astype(int)


# TODO: figure out if/how we can update an already trained model with only the new data
# -> see notes: use learning rate that takes the number of samples into account of previous training
# TODO: also figure out how to adapt a model to the current wearer -> should be a standard procedure somewhere...
# -> have a second look at the MAP tests in biokit
@local_registry.register
class Biokit_train(Node):
    """
    Updates a Hidden Markov Model Recognizer (for a BioKIT Feature Sequence Stream)

    Reads a given model or creates a new one if none is found.
    Every x seconds the received data will be used to update the model.
    Once the pipeline stops, the new model is written out to files.

    If the collected data includes unseen activities a new target is created using the passed parameter of default phases.
    If the data includes seen activities they are currently discarded. This is a TODO point, where these should also be used for training.

    Requires a BioKIT Feature Sequence Stream
    """

    channels_in = ["Data", "File", "Annotation", "Train"]
    channels_out = ["Training", "Text"]

    category = "BioKIT"
    description = ""

    example_init = {
        "name": "Train",
        "model_path": "./models",
        "atomList": [],
        "tokenDictionary": {},
        "train_iterations": 5,
        "token_insertion_penalty": 0,
        "rm_last_data_group": True
    }

    def __init__(self,
                 model_path,
                 phases_new_atom = 1,
                 phases_new_token = 1,
                 token_insertion_penalty = 20,
                 train_iterations = 5,
                 atomList = {},
                 tokenDictionary = {},
                 catch_all = "None",
                 name = "Train",
                 rm_last_data_group = True, # set to true if online annotation + training, set to false if offline training
                 compute_on=Location.PROCESS,
                 **kwargs):
        super().__init__(name, compute_on=compute_on, **kwargs)

        if self.compute_on is Location.SAME:
            # TODO: double check if/why this may be the case
            raise ValueError(f'compute_on may not be same for {str(self)}.')

        if model_path[-1] == '/':
            self.warn('Model Paths should not end with a slash, removing')
            model_path = model_path[:-1]

        self.model_path = model_path
        self.train_iterations = train_iterations
        self.atomList = atomList
        self.tokenDictionary = tokenDictionary
        self.phases_new_atom = phases_new_atom
        self.phases_new_token = phases_new_token
        self.token_insertion_penalty = token_insertion_penalty
        self.catch_all = catch_all
        self.rm_last_data_group = rm_last_data_group

        self.storage_annotation = []
        self.storage_data = []
        self.storage_file = []

        self.reco = None

        self.currently_training = False

    def _settings(self):
        return {\
            # "batch": self.batch,
            "token_insertion_penalty": self.token_insertion_penalty,
            "model_path": self.model_path,
            "train_iterations": self.train_iterations,
            "atomList": self.atomList,
            "tokenDictionary": self.tokenDictionary,
            "phases_new_atom": self.phases_new_atom,
            "phases_new_token": self.phases_new_token,
            "catch_all": self.catch_all,
            "rm_last_data_group": self.rm_last_data_group,
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
            atomList[atom] = self.atomList.get(atom, list(map(str, range(self.phases_new_atom))))
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
        self._emit_data('in _train', channel="Text")
        
        data = self.storage_data
        annotations = self.storage_annotation
        files = self.storage_file

        # Check lengths and process only the first data, keep everything in self tho!
        len_d, len_a, len_f = len(data), len(annotations), len(files)
        keep = min(len_d, len_a, len_f)
        if len_d != len_a or len_d != len_f or len_a != len_f:
            logger.warn(
                f"Data length ({len_d}) did not match annotation length ({len_a}) and file length ({len_f})"
            )
            data = np.array(data, dtype=object)[:keep]
            annotations = np.array(annotations, dtype=object)[:keep]
            files = np.array(files, dtype=object)[:keep]

        self._emit_data('checked lengths', channel="Text")

        if len(data) <= 0:
            self._emit_data('No data to Train on', channel="Text")
            return

        ### Prepare Data

        # get the diffs where either files changed or annotations changed
        diffs = np.clip(element_wise_diff(files) + element_wise_diff(annotations), 0, 1)
        # the indice splits are at the nonzero locations of the diffs +1 (as the diff is one index before the new value)
        split_indices = diffs.nonzero()[0] + 1
        
        # split the annotations and data arrays accordingly
        processedAnnotations = [[x[0]] for x in np.split(annotations, split_indices)]
        processedSequences = []
        for seq in np.split(data, split_indices):
            # this feels stupid, but kinda makes sense, as in the split we create FeatureVectors instead of Sequences, which then need to be stiched together
            # TODO: check if there is a more elegant / faster option to this
            # this is stupid. i should not have a node to_fs if we use it just to get the data out and in again.
            tmp = np.array([x.getVector() for x in seq]) 
            # print(tmp)
            pro_sq = BioKIT.FeatureSequence()
            pro_sq.setMatrix(tmp)
            processedSequences.append(pro_sq)

        if self.rm_last_data_group:
            # This is only useful in online training, as the last started annoation will never be finished exactly when the training starts
            processedAnnotations = processedAnnotations[:-1]
            processedSequences = processedSequences[:-1]
            self.info("Skipped last group, as its likely not finished yet, in accordance with the setting rm_last_data_group=", self.rm_last_data_group)

        processedAnnotations = np.array(processedAnnotations, dtype=object)
        processedSequences = np.array(processedSequences, dtype=object)

        if len(processedSequences) == 0:
            self._emit_data('No data to Train on', channel="Text")
            return

        self._emit_data('converted data format', channel="Text")


        ### Create Recognizer instance
        featuredimensionality = len(processedSequences[0][0])
        is_new = not os.path.exists(self.model_path) or not os.path.exists(f"{self.model_path}/dictionary")
        
        if not is_new:
            print('Adding new activities to existing model')
            self.reco = recognizer.Recognizer.createNewFromFile(
                self.model_path, sequenceRecognition=True)
        else:
            print('Adding new activities to new model')
            print('Feature dim:', featuredimensionality)
            # This is kinda ugly, but biokit does not allow empty dicts here :/
            self.reco = recognizer.Recognizer.createCompletelyNew(
                {
                    f"{self.catch_all}_1": ["0"],
                }, {self.catch_all: [f"{self.catch_all}_1"]},
                nrofmixtures=1, # will be auto expanded in merge and split training
                featuredimensionality=featuredimensionality, initDecoding=True)
            # self.reco = recognizer.Recognizer.createCompletelyNew({}, {}, 1, featuredimensionality=featuredimensionality)
        self.reco.setTokenInsertionPenalty(self.token_insertion_penalty)

       
        ### Figure out which tokens to train

        ### remove known tokens from processed list (they are already trained, and will atm not be updated, see future work)
        known_tokens = self.reco.getDictionary().getTokenList()
        if is_new:
            # catch all is not known (ie not trained) if the recognizer is new (it had to be added in init, as biokit throws an error otherwise)
            known_tokens.remove(self.catch_all)

        stored_tokens = np.unique(processedAnnotations)
        # add new tokens (except catch_all )
        for token in stored_tokens:
            if token != self.catch_all and not token in known_tokens:
                self.reco = self._add_token(
                    token, self.tokenDictionary.get(token, [f"{token}_{i}" for i in range(self.phases_new_token)]),
                    featuredimensionality=featuredimensionality,
                    nrofmixtures=1)

        # decide which tokens to train, ie which tokens have more new data now than the model on disk has
        available_samples = biokit_utils.calc_samples_per_token(processedAnnotations, processedSequences)
        if is_new or not os.path.exists(f'{self.model_path}/train_samples.json'):
            trained_samples = DefaultDict(int)
        else:
            with open(f'{self.model_path}/train_samples.json', 'r') as f:
                trained_samples = json.load(f)

        self.debug(trained_samples, available_samples)
        # keep tokens that are not in known_tokens unless the stored data is more than the trained data
        keep_tokens = list(filter(lambda x: (not x in known_tokens) or (available_samples.get(x, 0) > trained_samples.get(x, 0)), stored_tokens))
        # TODO: not sure if any is the right call here...
        idx = np.any(np.isin(processedAnnotations, keep_tokens), axis=-1)
        
        print(stored_tokens, keep_tokens)
        print(processedAnnotations.shape, processedSequences.shape, idx)

        ### Train
        if len(processedAnnotations[idx]) == 0:
            self.info("No new activities")
            return
        
        self.info("Learning Tokens:", keep_tokens)

        biokit_utils.train_sequence(self.reco, iterations=self.train_iterations, seq_tokens=processedAnnotations[idx], seq_data=processedSequences[idx], model_path=self.model_path)


    def _should_process(self, data=None, annotation=None, file=None, train=None):
        return data is not None \
            and annotation is not None \
            and (file is not None or not self._is_input_connected('File')) \
            and train in [0, 1] # train should be either 0 or 1, but not None

    def process(self, data, annotation, train, file=None, **kwargs):
        # remove batches! TODO: check and test this!
        self.storage_data.extend(np.array(data, dtype=object).flatten())
        annot = np.array(annotation).flatten()
        self.storage_annotation.extend(annot)

        if file is None:
            self.storage_file.extend(np.zeros_like(annot, dtype=int) - 1)
        else:
            self.storage_file.extend(np.array(file).flatten())


        self.info("Should train?", train, self.currently_training)
        if train and not self.currently_training:
            self.currently_training = True
            self.info('Now training')
            self._emit_data(1, channel="Training")
            
            if not os.path.exists(self.model_path):
                os.makedirs(self.model_path)

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
        else:
            self.info('Not training')
            self._emit_data(0, channel="Training")
            self._emit_data(f"[{str(self)}]\n      Waiting for instructions", channel="Text")

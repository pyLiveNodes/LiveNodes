from itertools import groupby
from typing import DefaultDict
import numpy as np

from livenodes.core.node import Node
from livenodes.biokit.biokit import BioKIT, logger, recognizer

from . import local_registry


@local_registry.register
class Biokit_train(Node):
    """
    Trains Hidden Markov Model Recognizer (for a BioKIT Feature Sequence Stream)

    Collects all data send to it along with the annotation and file information.
    Once it receives a Termination signal (read: no more data will be send) it trains a model with the given parameters and saves it to the specified path.

    Requires a BioKIT Feature Sequence Stream
    """

    channels_in = ['Data', 'File', 'Annotation', 'Termination']
    channels_out = []

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

    def __init__(self,
                 model_path,
                 token_insertion_penalty,
                 atomList,
                 tokenDictionary,
                 train_iterations,
                 name="Train",
                 **kwargs):
        super().__init__(name, **kwargs)

        self.model_path = model_path
        self.atomList = atomList
        self.tokenDictionary = tokenDictionary
        self.train_iterations = train_iterations
        self.token_insertion_penalty = token_insertion_penalty

        self.data = []
        self.annotations = []
        self.files = []

    def _settings(self):
        return {\
            # "batch": self.batch,


            "token_insertion_penalty": self.token_insertion_penalty,
            "model_path": self.model_path,
            "atomList": self.atomList,
            "tokenDictionary": self.tokenDictionary,
            "train_iterations": self.train_iterations
        }

    def _train(self):
        processedTokens = DefaultDict(list)
        processedSequences = []
        processedAnnotations = []

        # TODO: clean this up and make sure we don't need store the data twice (once on self and once in fs)
        for _, g in groupby(zip(self.data, self.annotations, self.files),
                            key=lambda x: x[2]):
            g = list(g)
            pro_sq = BioKIT.FeatureSequence()
            for x in g:
                pro_sq.append(x[0])
            processedSequences.append(pro_sq)
            tmp_an = []
            for atom, gg in groupby(g, key=lambda x: x[1]):
                tmp_an.append(atom)
                pro_sq = BioKIT.FeatureSequence()
                for x in gg:
                    pro_sq.append(x[0])
                processedTokens[atom].append(pro_sq)
            processedAnnotations.append(tmp_an)

        print(processedTokens.keys())

        self.reco = recognizer.Recognizer.createCompletelyNew(
            self.atomList, self.tokenDictionary, 1,
            len(processedSequences[0][0]), True)
        self.reco.setTokenInsertionPenalty(self.token_insertion_penalty)

        self.reco.setTrainerType(
            recognizer.TrainerType('merge_and_split_trainer'))
        config = self.reco.trainer.getConfig()
        config.setSplitThreshold(500)
        config.setMergeThreshold(100)
        config.setKeepThreshold(10)
        config.setMaxGaussians(10)

        self.info('=== Initializaion ===')
        for atom in processedTokens:
            for trainingData in processedTokens[atom]:
                self.reco.storeTokenSequenceForInit(
                    trainingData, [atom],
                    fillerToken=-1,
                    addFillerToBeginningAndEnd=False)
        self.reco.initializeStoredModels()

        # TODO: not sure if we actually need both (train token and train sequence) and how/if we can even combine token + seq here...
        self.info('=== Train Tokens ===')
        # Use the fact that we know each tokens start and end
        for i in range(self.train_iterations[0]):
            self.info(f'--- Iteration {i} ---')
            for atom in processedTokens:
                for trainingData in processedTokens[atom]:
                    # Says sequence, but is used for small chunks, so that the initial gmm training etc is optimized before we use the full sequences
                    self.reco.storeTokenSequenceForTrain(
                        trainingData, [atom],
                        fillerToken=-1,
                        ignoreNoPathException=True,
                        addFillerToBeginningAndEnd=False)
            self.reco.finishTrainIteration()

        self.info('=== Train Sequence ===')
        # not sure if this is even needed tbh, TODO: try and document
        for i in range(self.train_iterations[1]):
            self.info(f'--- Iteration {i} ---')
            for sequence, annotation in zip(processedSequences,
                                            processedAnnotations):
                self.reco.storeTokenSequenceForTrain(
                    sequence,
                    annotation,
                    fillerToken=-1,
                    ignoreNoPathException=True,
                    addFillerToBeginningAndEnd=False)
            self.reco.finishTrainIteration()

        # Save the model
        self.reco.saveToFiles(self.model_path)

    def receive_data_end(self):
        # assume we never loose data, then these should be the same
        len_d, len_a, len_f = len(self.data), len(self.annotations), len(
            self.files)
        keep = min(len_d, len_a, len_f)
        if len_d != len_a or len_d != len_f or len_a != len_f:
            logger.warn(
                f"Data length ({len_d}) did not match annotation length ({len_a}) and file length ({len_f})"
            )
            self.data = self.data[:keep]
            self.annotations = self.annotations[:keep]
            self.files = self.files[:keep]

        self._train()

    def _should_process(self,
                        data=None,
                        annotation=None,
                        file=None,
                        termination=None):
        return (data is not None \
            and annotation is not None \
            and file is not None)

    def process(self,
                data=None,
                annotation=None,
                file=None,
                termination=None,
                **kwargs):
        if data is not None:
            # remove batches!
            self.files.extend(np.array(file).flatten())
            # self.info(np.unique(np.array(annotation).flatten(), return_counts=True))
            self.annotations.extend(np.array(annotation).flatten())
            self.data.extend(data)

        if termination:
            self.info('Starting Training')
            self.receive_data_end()

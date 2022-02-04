from itertools import groupby
from typing import DefaultDict
import numpy as np
from .node import Node

import recognizer
import logger



# TODO: figure out if/how we can update an already trained model with only the new data
class Biokit_train(Node):
    def __init__(self, model_path, token_insertion_penalty, atomList, tokenDictionary, train_iterations, name="Recognizer", dont_time=False):
        super().__init__(name, dont_time)

        self.model_path = model_path
        self.atomList = atomList
        self.tokenDictionary = tokenDictionary
        self.train_iterations = train_iterations
        self.token_insertion_penalty = token_insertion_penalty

        self.data = []
        self.annotations = []
        self.files = []

    def _get_setup(self):
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

        for _, g in groupby(zip(self.data, self.annotations, self.files), key=lambda x: x[2]):
            processedSequences.append([x[0] for x in g])
            processedAnnotations.append([x[1] for x in g])
            for atom, gg in groupby(g, key=lambda x: x[1]):
                processedTokens[atom].append([x[0] for x in gg])


        self.reco = recognizer.Recognizer.createCompletelyNew(self.atomList, self.tokenDictionary, 1, processedSequences[0].getDimensionality(), True)
        self.reco.setTokenInsertionPenalty(self.token_insertion_penalty)

        self.reco.setTrainerType(recognizer.TrainerType('merge_and_split_trainer'))
        config = self.reco.trainer.getConfig()
        config.setSplitThreshold(500)
        config.setMergeThreshold(100)
        config.setKeepThreshold(10)
        config.setMaxGaussians(10)


        logger.info('=== Initializaion ===')
        for atom in processedTokens:
            for atoms, trainingData in processedTokens[atom]:
                self.reco.storeTokenSequenceForInit(trainingData, atoms, fillerToken=-1, addFillerToBeginningAndEnd=False)
        self.reco.initializeStoredModels()


        # TODO: not sure if we actually need both (train token and train sequence) and how/if we can even combine token + seq here...
        logger.info('=== Train Tokens ===')
        # Use the fact that we know each tokens start and end
        for i in range(self.train_iterations[0]):
            logger.info(f'--- Iteration {i} ---')
            for atom in processedTokens:
                for atoms, trainingData in processedTokens[atom]:
                    # Says sequence, but is used for small chunks, so that the initial gmm training etc is optimized before we use the full sequences
                    self.reco.storeTokenSequenceForTrain(trainingData, atoms, fillerToken=-1, ignoreNoPathException=True, addFillerToBeginningAndEnd=False)
            self.reco.finishTrainIteration()


        logger.info('=== Train Sequence ===')
        # not sure if this is even needed tbh, TODO: try and document
        for i in range(self.train_iterations[1]):
            logger.info(f'--- Iteration {i} ---')
            for sequence, annotation in zip(processedSequences, processedAnnotations):
                self.reco.storeTokenSequenceForTrain(sequence, annotation, fillerToken=-1, ignoreNoPathException=True, addFillerToBeginningAndEnd=False)
            self.reco.finishTrainIteration()

        # Save the model
        self.reco.saveToFiles(self.model_path)


    def receive_data_end(self, data_frame, **kwargs):
        len_d, len_a, len_f = len(self.data), len(self.annotations), len(self.files)
        keep = min(len_d, len_a, len_f) 
        if len_d != len_a or len_d != len_f or len_a != len_f:
            logger.warning(f"Data length ({len_d}) did not match annotation length ({len_a}) and file length ({len_f})")
            self.data = self.data[:keep]
            self.annotations = self.annotations[:keep]
            self.files = self.files[:keep]
            
        self._train()

    def receive_file(self, files, **kwargs):
        self.files.extend(files)

    def receive_annotation(self, annotation, **kwargs):
        self.annotations.extend(annotation)

    def receive_data(self, fs, **kwargs):
        self.data.extend(fs)



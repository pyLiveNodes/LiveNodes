from functools import partial
from itertools import groupby
import traceback
import numpy as np
from filelock import FileLock

import livenodes.biokit.utils as biokit_utils

from livenodes.core.node import Node
from livenodes.biokit.biokit import BioKIT, logger, recognizer

from . import local_registry

def element_wise_diff(arr):
    w = np.array(arr, dtype=object)
    return np.concatenate([[False], w[1:] != w[:-1]], axis=0).astype(int)

@local_registry.register
class Biokit_train(Node):
    """
    Trains Hidden Markov Model Recognizer (for a BioKIT Feature Sequence Stream)

    Collects all data send to it along with the annotation and file information.
    Once it receives a Termination signal (read: no more data will be send) it trains a model with the given parameters and saves it to the specified path.

    Requires a BioKIT Feature Sequence Stream
    """

    channels_in = ['Data', 'File', 'Annotation', 'Train']
    channels_out = ['Text']

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

        self.currently_training = False

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
        # we should never ever change the self.storage data as this will make everything out of sync!
        # ie if len(data) = 10 and len(annotation) = 9 (and 1 is in queue to be added) then we remove the last data, but the queue will still be added.
        #   -> every new label is shifted by 1 package. this propagates until nothing fits to nothing anymore
        # Note: this is a very unlikely scenario due to the clock mechanism, but still.
        self._emit_data('in _train', channel="Text")
        data = self.data
        annotations = self.annotations
        files = self.files

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

        # get the diffs where either files changed or annotations changed
        diffs = np.clip(element_wise_diff(files) + element_wise_diff(annotations), 0, 1)
        # the indice splits are at the nonzero locations of the diffs +1 (as the diff is one index before the new value)
        split_indices = diffs.nonzero()[0] + 1
        
        # split the annotations and data arrays accordingly
        processedAnnotations = np.split(annotations, split_indices)
        processedSequences = []
        for seq in np.split(data, split_indices):
            # this feels stupid, but kinda makes sense, as in the split we create FeatureVectors instead of Sequences, which then need to be stiched together
            # TODO: check if there is a more elegant / faster option to this
            # this is stupid. i should not have a node to_fs if we use it just to get the data out and in again.
            tmp = np.array([x.getVector() for x in seq]) 
            pro_sq = BioKIT.FeatureSequence()
            pro_sq.setMatrix(tmp)
            processedSequences.append(pro_sq)

        self._emit_data('converted data format', channel="Text")

        self.reco = recognizer.Recognizer.createCompletelyNew(
            self.atomList, self.tokenDictionary, 1,
            len(processedSequences[0][0]), True)
        self.reco.setTokenInsertionPenalty(self.token_insertion_penalty)

        self._emit_data('Processed all data - starting training', channel="Text")
        biokit_utils.train_sequence(self.reco, iterations=self.train_iterations, seq_tokens=processedAnnotations, seq_data=processedSequences, model_path=self.model_path, emit_fn=partial(self._emit_data, channel='Text'))

    def _should_process(self,
                        data=None,
                        annotation=None,
                        file=None,
                        train=None):
        return data is not None \
            and annotation is not None \
            and file is not None \
            and (train in [0, 1] or not self._is_input_connected('Train'))

    def process(self,
                data=None,
                annotation=None,
                file=None,
                train=None,
                **kwargs):

        if data is not None:
            # remove batches!
            self.files.extend(np.array(file).flatten())
            # self.info(np.unique(np.array(annotation).flatten(), return_counts=True))
            self.annotations.extend(np.array(annotation).flatten())
            self.data.extend(np.array(data, dtype=object).flatten())

            self._emit_data(f"Collected {len(self.annotations)} samples.", channel='Text')

        if train and not self.currently_training:
            self.currently_training = True
            self.info('Starting Training')
            try:
                with biokit_utils.model_lock(self.model_path):
                    self.info('Got lock')
                    self._train()
            except Exception as err:
                print(traceback.format_exc())
                print(err)
            self.currently_training = False

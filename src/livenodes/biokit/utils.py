from collections import defaultdict
import json 
import os
from filelock import FileLock

from livenodes.biokit.biokit import BioKIT, logger, recognizer

def calc_samples_per_token(seq_tokens, seq_data):
    training_data = defaultdict(int)
    for tokens, data in zip(seq_tokens, seq_data):
        samples_estimate = len(data) / len(tokens)
        for token in tokens:
            training_data[token] += samples_estimate
    return training_data

def noop (*args):
    pass

def train_sequence(biokit_hmm, iterations, seq_tokens, seq_data, model_path, emit_fn=noop):

    # TODO: implement version that ignores seq_data if it contains a channel with only zeros! (as this will lead to a "covariance is singular cannot invert error in biokit")
    # alternatively: create nodes to do so

    ### Setup trainer
    biokit_hmm.setTrainerType(
        recognizer.TrainerType('merge_and_split_trainer'))
    config = biokit_hmm.trainer.getConfig()
    config.setSplitThreshold(500)
    config.setMergeThreshold(100)
    config.setKeepThreshold(10)
    config.setMaxGaussians(10)

    logger.info('=== Initializaion ===')
    for tokens, data in zip(seq_tokens, seq_data):
        biokit_hmm.storeTokenSequenceForInit(
            data, tokens,
            fillerToken=-1,
            addFillerToBeginningAndEnd=False)
    biokit_hmm.initializeStoredModels()
    emit_fn('Finished Initialization')

    logger.info('=== Train Tokens ===')
    # Use the fact that we know each tokens start and end
    for i in range(iterations):
        logger.info(f'--- Iteration {i + 1} ---')
        for tokens, data in zip(seq_tokens, seq_data):
            # Says sequence, but is used for small chunks, so that the initial gmm training etc is optimized before we use the full sequences
            biokit_hmm.storeTokenSequenceForTrain(
                data, tokens,
                fillerToken=-1,
                ignoreNoPathException=True,
                addFillerToBeginningAndEnd=False)
        biokit_hmm.finishTrainIteration()
        emit_fn(f'Finished Iteration: {i + 1}')
    
    prev_counts = {}
    train_samples_count_file = f'{model_path}/train_samples.json'
    # TODO: there is probably a more elegant version to read and update this file...
    if os.path.exists(train_samples_count_file):
        with open(train_samples_count_file, 'r') as f:
            prev_counts = json.load(f)
    
    with open(train_samples_count_file, 'w') as f:
        json.dump({**prev_counts, **calc_samples_per_token(seq_tokens, seq_data)}, f, indent=4)
    
    biokit_hmm.saveToFiles(model_path)
    emit_fn(f'Written Model to Disc: {model_path}')


def model_lock(model_path, timeout=0.1):
    return FileLock(f"{model_path}.lock", timeout=timeout)
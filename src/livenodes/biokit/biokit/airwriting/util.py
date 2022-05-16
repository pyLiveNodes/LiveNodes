import BioKIT
from . import db
import adc
import os
import numpy
import numpyutil


class FeatureSequenceStorage:
    """
    Precomputes and stores features sequences in memory.
    """

    def __init__(self, config, prepro):
        print("Initialize storage object for FeatureSequences")
        self.storage = {}
        self.config = config
        self.prepro = prepro
        if self.config.trainset:
            for recording in self.config.trainset.recordings:
                self.put(recording)
        if self.config.testset:
            for recording in self.config.testset.recordings:
                self.put(recording)

    def put(self, recording):
        filename = os.path.join(self.config.data_basedir,
                                recording.experiment.base_dir,
                                recording.filename)
        mcfs = self.prepro.process(filename)
        fs = mcfs[0]
        self.storage[recording.id] = fs

    def get(self, recording_id):
        return (self.storage[recording_id])

    def wipe(self):
        self.storage = {}


def computeClassStats(janusdb, ids):
    """
    Computes basic statistics for each class
    
    Computes mean and standard deviation of the length in samples for each 
    class (character) on the recordings given by the respective database ids. 
    Currently works on old flat Janus style sqlite database.
    
    Keyword arguments:
    janusdb - instance of db.JanusDb
    ids     - list of janus id strings
    """

    samplecounts = dict()
    basedir = "/project/AMR/Handwriting/data/"
    for id in ids:
        query = janusdb.session.query(db.Recording).\
                        filter(db.Recording.janusid == id)
        recording = query.one()
        if len(recording.text) > 1:
            text = "_"
        else:
            text = recording.text
        filepath = os.path.join(basedir, "v" + recording.expid, "data",
                                recording.filename)
        data = adc.read(filepath)
        count = data.shape[0]
        if text not in samplecounts:
            samplecounts[text] = []
        samplecounts[text].append(count)
    #compute mean and stddev
    stats = dict()
    for text, counts in samplecounts.items():
        mean = numpy.mean(counts)
        stddev = numpy.std(counts)
        stats[text] = {'mean': mean, 'stddev': stddev}
    return stats


def writeMcfsToAdc(mcfs, path):
    """
       Write a mcfs to an ADC file
       """
    ar = numpyutil.mcfs2array(mcfs)
    adc.write(ar, path)

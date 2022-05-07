from . import db
import BioKIT
import argparse
import pprint
import tempfile
import subprocess
import os
import socket
import shutil
from . import db
from . import airwritingUtil
import align
import time
import tempfile
from .runjanus import *
import pdb
import datetime
import visualization as vis


def log(level, text):
    print("Python log: " + str(datetime.datetime.now()) + " - " + level +
          ": " + text)


class AirwritingRecognizer:

    def __init__(self, session):
        """
        Constructs an instance of the recognizer.

        Keyword arguments:
        session - a valid session of an db.AirDb instance
        """
        self.session = session

    def setup(self, config):
        """
        Setup all necessary biokit classes to performa a decoding

        Keyword arguments:
        config - Instance of db.ModelParameters class containing all parameters
        """

        #dynamically import the preprocessing class which the user specified
        #generally considered as bad practice but fine for us because we want
        #users to define their own code
        prepro_module = config.preprocessing.biokit_desc
        pp = __import__(prepro_module)
        #import fileprepro as pp
        self.prepro = pp.PrePro()

        self.gaussianContainerSet = BioKIT.GaussianContainerSet()
        self.gaussianContainerSet.readDescFile("gaussian_desc")
        self.gaussianContainerSet.loadDataFile("gaussian_data")

        log("Info",
            "Gaussian container set is: " + str(self.gaussianContainerSet))

        self.gaussMixtureSet = BioKIT.GaussMixturesSet(
            self.gaussianContainerSet)
        self.gaussMixtureSet.readDescFile("mixture_desc")
        self.gaussMixtureSet.loadDataFile("mixture_data")

        log("Info", "GaussMixtureSet is: " + str(self.gaussMixtureSet))

        self.gmmScorer = BioKIT.GmmFeatureVectorScorer(self.gaussMixtureSet)
        self.cacheScorer = BioKIT.CacheFeatureVectorScorer(self.gmmScorer)

        log("Info", "Generating model mapper")

        self.modelMapper = BioKIT.ModelMapper.ReadTopology(
            self.cacheScorer, "distrib_tree", "topology_tree", "topologies",
            "transitions")

        log("Info", "Loading atoms from janus phonesSet")
        self.atomMap = BioKIT.AtomManager()
        self.atomMap.readAtomManager("phones")

        log("Info", "Loading dictionary")
        self.dictionary = BioKIT.Dictionary(self.atomMap)
        self.dictionary.readDictionary(str(config.dictionary.file))
        self.dictionary.config().setStartToken("<s>")
        self.dictionary.config().setEndToken("</s>")
        self.dictionary.config().setUnknownToken("<UNK>")

        #dictionary.addToken("SIL", ["SIL"])
        #dictionary.addToken("_", ["_"])

        log("Info", "Generating search vocabulary from dictionary")
        self.vocabulary = BioKIT.SearchVocabulary(self.dictionary)

        if config.contextmodel.type.name == "grammar":
            self.grammar = BioKIT.GrammarTokenSequenceModel(self.dictionary)
            ######### dirty hack, generate gra filename from nav file
            gra_file = os.path.splitext(str(
                config.contextmodel.file))[0] + ".gra"
            self.grammar.readSimplifiedGrammar(gra_file)
            self.tokenSequenceModel = self.grammar
        elif config.contextmodel.type.name == "ngram":
            self.ngram = BioKIT.NGram(self.dictionary)
            self.ngram.readArpaFile(str(config.contextmodel.file),
                                    self.vocabulary)
            self.tokenSequenceModel = self.ngram

        self.tokenSequenceModel = BioKIT.ZeroGram(self.dictionary)

        log("Info", "Making search graph")
        #self.beams = BioKIT.Beams(config.biokitconfig.hypo_beam,
        #                           config.biokitconfig.hypo_topn,
        #                           config.biokitconfig.active_node_beam,
        #                           config.biokitconfig.active_node_topn,
        #                           config.biokitconfig.final_node_beam,
        #                           config.biokitconfig.final_node_topn)

        self.beams = BioKIT.Beams(1, 2, 1000, 10000, 1, 100)
        print((self.beams))
        self.tokenInsertionPenalty = 10000

        self.tokenSequenceModelWeight = config.biokitconfig.tokensequencemodel_weight
        self.tokenInsertionPenalty = config.biokitconfig.token_insertion_penalty
        self.searchGraphHandler = BioKIT.SearchGraphHandler(
            self.tokenSequenceModel, self.dictionary, self.vocabulary,
            self.modelMapper, self.cacheScorer, self.beams, 1, 10000)
        self.searchGraphHandler.createDotGraph("searchgraph.dot")
        self.searchGraphHandler.setKeepHyposAlive(True)

        #self.searchGraphHandler.createTsmLookAhead(4)
        #self.searchGraphHandler.getTsmLookAhead().config().setTsmWeight(self.tokenSequenceModelWeight);

        log("Info", "Creating BioKIT")
        self.decoder = BioKIT.Decoder(self.searchGraphHandler)

        self.trainset = config.trainset
        self.testset = config.testset

        self.data_basedir = config.data_basedir

    def extractfeat(self, filename):
        mcfs = self.prepro.process(filename)
        log(
            "Info", "size of feature matrix: (%s, %s)" %
            (mcfs[0].getLength(), mcfs[0].getDimensionality()))
        return mcfs

    def decode(self, mcfs, plot=True):
        """
        decode given adc file
        """

        self.decoder.search(mcfs, True)
        results = self.decoder.extractSearchResult()
        log("Info", "search results")
        for res in results:
            log("Info", "hypo: %s, score: %s" % (res.toString(), res.score))
        if len(results) != 0:
            bestResult = results[0].toString()
        else:
            bestResult = ""
        cleanResult = bestResult.replace("SIL", "").replace("_", "").rstrip()
        if plot:
            path = self.Decoder.traceViterbiPath()
            for item in path:
                print(("modelid: %s, partial score: %s" %
                       (self.gmmScorer.getModelName(
                           item.mModelId), item.mPartialScore)))
            pp = vis.PathPlot(path, mcfs[0],
                              self.searchGraphHandler.getSearchGraph(),
                              self.gmmScorer)
            pp.plot("free decoding")

    def forcedalign(self, mcfs, tokenName, plot=True):

        trainingsID = self.dictionary.getTokenIds(tokenName)
        print(trainingsID)
        # create search graph for path mapping
        """
        TRAIN
        """
        sil = self.dictionary.getTokenIds("SIL")[0]

        handler = BioKIT.SearchGraphHandler(self.dictionary, trainingsID, sil,
                                            self.modelMapper, self.gmmScorer,
                                            self.beams,
                                            self.tokenSequenceModelWeight,
                                            self.tokenInsertionPenalty)

        handler.setKeepHyposAlive(True)
        #graph = handler.getSearchGraph()
        try:
            decoder = BioKIT.Decoder(handler)
            decoder.search(mcfs, True)
            path = decoder.traceViterbiPath()
            if plot:
                pp = vis.PathPlot(path, mcfs[0], handler, self.gmmScorer)
                pp.plot("forced alignment")
            return path
        except RuntimeError as e:
            print(('Error in forced alignment for %s, error was: %s' %
                   (tokenName, str(e))))
            return None

    def decode_set(self, set):
        """
        decode a given set of recordings and return results.

        Keyword arguments:
        set - the dataset to decode given as db.Dataset
        """
        log("Info", "decode set: %s" % (set.recordings, ))
        resultlist = []
        for recording in set.recordings:
            filename = os.path.join(self.data_basedir,
                                    recording.experiment.base_dir,
                                    recording.filename)
            log("Info", "decode: %s" % (filename, ))
            mcfs = self.prepro.process(filename)
            log(
                "Info", "size of feature matrix: (%s, %s)" %
                (mcfs[0].getLength(), mcfs[0].getDimensionality()))

            self.decoder.search(mcfs, True)
            results = self.decoder.extractSearchResult()
            log("Info", "search results")
            for res in results:
                log("Info",
                    "hypo: %s, score: %s" % (res.toString(), res.score))
            if len(results) != 0:
                bestResult = results[0].toString()
            else:
                bestResult = ""
            cleanResult = bestResult.replace("SIL", "").replace("_",
                                                                "").rstrip()
            result = {
                'reference': recording.reference,
                'hypothesis': cleanResult
            }
            log("Info", str(result))
            resultlist.append(result)
        return resultlist


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform training with " +
                                     "janus and decoding with biokit")
    parser.add_argument('database', help="sqlite database file")
    parser.add_argument('configid', help="row id of job to run")
    parser.add_argument('file', help="ADC file to decode")
    parser.add_argument("reference", help="reference string")
    parser.add_argument('--datadir', default="/project/AMR/Handwriting/data")
    args = parser.parse_args()

    print()
    print("****** Starting BioKit Airwriting decoding with args:")
    pprint.pprint(args)
    print()

    airdb = db.AirDb(args.database)
    config = airdb.session.query(
        db.Configuration).filter(db.Configuration.id == args.configid).one()

    log("Info", "Using config:")
    pprint.pprint(config.__dict__)
    print()

    airrec = AirwritingRecognizer(airdb.session)
    airrec.setup(config)
    mcfs = airrec.extractfeat(args.file)
    airrec.decode(mcfs)
    #airrec.forcedalign(mcfs, args.reference)
    vis.show()

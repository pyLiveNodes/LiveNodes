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
        self.blamepath = None

    def setup(self, config, modelparam, tmpdir=None):
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
        self.prepro = pp.PrePro()

        #modelparam = self.session.query(db.ModelParameters).\
        #             filter_by(configuration = config,
        #             iteration = iteration).all()
        log("Info", "Recognizer using models: %s" % modelparam)
        #modelparam = modelparam[0]

        if not tmpdir:
            tmpdir = tempfile.mkdtemp()
        os.chdir(tmpdir)
        self.blamepath = tmpdir

        db.write_blob(modelparam.gaussian_data, "gaussian_data")
        db.write_blob(modelparam.gaussian_desc, "gaussian_desc")
        self.gaussianContainerSet = BioKIT.GaussianContainerSet()
        self.gaussianContainerSet.readDescFile("gaussian_desc")
        self.gaussianContainerSet.loadDataFile("gaussian_data")

        log("Info",
            "Gaussian container set is: " + str(self.gaussianContainerSet))

        db.write_blob(modelparam.mixture_data, "mixture_data")
        db.write_blob(modelparam.mixture_desc, "mixture_desc")
        self.gaussMixtureSet = BioKIT.GaussMixturesSet(
            self.gaussianContainerSet)
        self.gaussMixtureSet.readDescFile("mixture_desc")
        self.gaussMixtureSet.loadDataFile("mixture_data")

        log("Info", "GaussMixtureSet is: " + str(self.gaussMixtureSet))

        self.gmmScorer = BioKIT.GmmFeatureVectorScorer(self.gaussMixtureSet)
        self.cacheScorer = BioKIT.CacheFeatureVectorScorer(self.gmmScorer)

        log("Info", "Loading atoms from janus phonesSet")
        db.write_blob(modelparam.phones, "phones")
        self.atomMap = BioKIT.AtomManager()
        self.atomMap.readAtomManager("phones")

        log("Info", "Generating model mapper")

        db.write_blob(modelparam.distrib_tree, "distrib_tree")
        db.write_blob(modelparam.topology_tree, "topology_tree")
        db.write_blob(modelparam.topologies, "topologies")
        db.write_blob(modelparam.transitions, "transitions")
        self.modelMapper = BioKIT.ModelMapper.ReadTopology(
            self.cacheScorer, self.atomMap, "distrib_tree", "topology_tree",
            "topologies", "transitions")

        log("Info", "Loading dictionary")
        self.dictionary = BioKIT.Dictionary(self.atomMap)
        self.dictionary.registerAttributeHandler("FILLER",
                                                 BioKIT.NumericValueHandler())
        self.dictionary.readDictionary(str(config.dictionary.file))
        self.dictionary.config().setStartToken("<s>")
        self.dictionary.config().setEndToken("</s>")
        self.dictionary.config().setUnknownToken("<UNK>")

        #dictionary.addToken("SIL", ["SIL"])
        #dictionary.addToken("_", ["_"])

        log("Info", "Generating search vocabulary from dictionary")
        self.vocabulary = BioKIT.SearchVocabulary(self.dictionary)

        if config.contextmodel.type.name == "grammar":
            #self.grammar = BioKIT.GrammarTokenSequenceModel(self.dictionary)
            ######### dirty hack, generate gra filename from nav file
            #gra_file = os.path.splitext(str(config.contextmodel.file))[0] + ".gra"
            #self.grammar.readSimplifiedGrammar(gra_file)
            # do not actually use the grammar but use a tweaked 0-gram
            # with a very high tokenInsertionPenalty
            self.grammar = BioKIT.ZeroGram(self.dictionary)
            self.tokenSequenceModel = self.grammar
            #self.tokenInsertionPenalty = 10000
        elif config.contextmodel.type.name == "ngram":
            self.ngram = BioKIT.NGram(self.dictionary)
            self.ngram.readArpaFile(str(config.contextmodel.file),
                                    self.vocabulary)

            log('info', 'Creating tokensequence model with fillers')
            self.fillerWrapper = BioKIT.FillerWrapper(self.ngram,
                                                      self.dictionary,
                                                      'FILLER')

            log('info', 'Creating cache tokensequence model')
            self.cacheTsm = BioKIT.CacheTokenSequenceModel(
                self.fillerWrapper, self.dictionary)

            self.tokenSequenceModel = self.cacheTsm

        log("Info", "Making search graph")

        self.beams = BioKIT.Beams(config.biokitconfig.hypo_beam,
                                  config.biokitconfig.hypo_topn,
                                  config.biokitconfig.final_hypo_beam,
                                  config.biokitconfig.final_hypo_topn,
                                  config.biokitconfig.lattice_beam)
        print((self.beams))

        self.tokenSequenceModelWeight = config.biokitconfig.languagemodel_weight
        self.tokenInsertionPenalty = config.biokitconfig.token_insertion_penalty
        print(("tsm weight: %s, tokeninsertionpenalty: %s" %
               (self.tokenSequenceModelWeight, self.tokenInsertionPenalty)))
        self.searchGraphHandler = BioKIT.SearchGraphHandler(
            self.tokenSequenceModel, self.dictionary, self.vocabulary,
            self.modelMapper, self.cacheScorer, self.beams,
            float(self.tokenSequenceModelWeight),
            float(self.tokenInsertionPenalty))
        #        self.searchGraphHandler.createDotGraph("searchgraph.dot")

        self.searchGraphHandler.createTsmLookAhead(-1)
        self.searchGraphHandler.getTsmLookAhead().config().setTsmWeight(
            self.tokenSequenceModelWeight)
        self.searchGraphHandler.getTsmLookAhead().config().setMaxNodeCache(
            3000)

        log("Info", "Creating BioKIT")
        self.decoder = BioKIT.Decoder(self.searchGraphHandler)

        self.trainset = config.trainset
        self.testset = config.testset

        self.data_basedir = config.data_basedir

    def _get_blamepath(self):
        if not self.blamepath:
            self.blamepath = tempfile.mkdtemp()
        return self.blamepath

    def decode(self, recording, errorblame=False, generatePath=False):
        filename = os.path.join(self.data_basedir,
                                recording.experiment.base_dir,
                                recording.filename)
        log("Info", "decode: %s" % (filename, ))
        mcfs = self.prepro.process(filename)
        log(
            "Info", "size of feature matrix: (%s, %s)" %
            (mcfs[0].getLength(), mcfs[0].getDimensionality()))

        if errorblame:
            self.searchGraphHandler.setKeepHyposAlive(True)
            filename = "hyp.%s.snp" % recording.id
            snapshotName = os.path.join(self._get_blamepath(), filename)
            log("Info", "generate hypothesis snapshot in %s" % snapshotName)
            self.searchGraphHandler.createSnapshot(
                snapshotName, self.tokenSequenceModelWeight,
                self.tokenInsertionPenalty)

        if generatePath:
            self.searchGraphHandler.setKeepHyposAlive(True)
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
        result = {'reference': recording.reference, 'hypothesis': bestResult}
        log("Info", str(result))
        if generatePath:
            self.path = self.searchGraphHandler.traceViterbiPath()
        if errorblame:
            self.blame(mcfs[0], recording)
        return (result)

    def decode_set(self, set, errorblame=False):
        """
        decode a given set of recordings and return results.

        Keyword arguments:
        set - the dataset to decode given as db.Dataset
        """
        log("Info", "decode set: %s" % (set.recordings, ))
        resultlist = []
        if errorblame:
            self.blamelogs = {}
            self.confusionHandler = BioKIT.ConfusionHandler(self.gmmScorer)
            self.blamelog_fh = open("blamelog.csv", "w")
        for recording in set.recordings:
            result = self.decode(recording, errorblame)
            resultlist.append(result)
        if errorblame:
            self.blamelog_fh.close()
        return resultlist

    def blame(self, fs, recording, flexibility=0.7, hypos=200):
        log("Info", "Perform Error Blaming")
        filename = os.path.join(self.data_basedir,
                                recording.experiment.base_dir,
                                recording.filename)
        self.blameReference(fs, recording)
        errorBlamer = BioKIT.ErrorBlamer(self.dictionary, flexibility,
                                         self.gmmScorer)
        hypsnapshot = os.path.join(self._get_blamepath(),
                                   "hyp.%s.snp" % recording.id)
        refsnapshot = os.path.join(self._get_blamepath(),
                                   "ref.%s.snp" % recording.id)
        shrinksnapshot = os.path.join(self._get_blamepath(),
                                      "shrink.%s.snp" % recording.id)
        BioKIT.SnapshotHandler.Shrink(hypsnapshot, hypos, shrinksnapshot)
        hypsnapshot = shrinksnapshot
        log("Info", "load snapshots %s, %s" % (hypsnapshot, refsnapshot))
        errorBlamer.loadSnapshots(hypsnapshot, refsnapshot)
        self.blamelogs[recording.id] = errorBlamer.blameAndWriteUtterance()
        self.blamelog_fh.write("Blame assignment for %s:\n" % recording.id)
        self.blamelog_fh.write(errorBlamer.blameAndWriteUtterance() + "\n\n")
        self.confusionHandler.collectConfusions(hypsnapshot, refsnapshot)

    def getBlameResults(self):
        """
        Return blame log and confusion mapping and reset error blaming
        """
        confusion = self.confusionHandler.toCSV()
        with open("confusion_map.csv", "w") as f:
            f.write(confusion)
        blamelogs = self.blamelogs
        self.confusionHandler = None
        self.blamelogs = None
        return (blamelogs, confusion)

    def blameReference(self, fs, recording):
        """
        Perform a forced viterbi alignment and return the viterbi path.

        Returns the viterbi path or None if no path was found.

        Keyword arguments:
        fs - a sample Feature Sequence
        listOfTokenNames - ordered list of token names, that are to be trained
        """
        tokenIDs = []
        listOfTokenNames = recording.reference.encode('ascii').split()
        for tokenName in listOfTokenNames:
            tokenIds = self.dictionary.getTokenIds(tokenName)
            assert (len(tokenIds) == 1)
            tokenIDs.append(tokenIds[0])

        print(("building search graph for %s (%s)" %
               (listOfTokenNames, tokenIDs)))
        handler = BioKIT.SearchGraphHandler(self.dictionary, tokenIDs, -1,
                                            True, self.modelMapper,
                                            self.gmmScorer, self.beams,
                                            self.tokenSequenceModelWeight,
                                            self.tokenInsertionPenalty)

        handler.setKeepHyposAlive(True)
        decoder = BioKIT.Decoder(handler)

        filename = "ref.%s.snp" % recording.id
        snapshotName = os.path.join(self._get_blamepath(), filename)
        handler.createSnapshot(snapshotName, self.tokenSequenceModelWeight,
                               self.tokenInsertionPenalty)
        decoder.search([fs], True)
        print(("forcedalign result: %s" %
               decoder.extractSearchResult()[0].toString()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform training with " +
                                     "janus and decoding with biokit")
    parser.add_argument('database', help="sqlite database file")
    parser.add_argument('id', help="row id of config to run")
    parser.add_argument('iter', help="number of training iterations")
    parser.add_argument('--datadir', default="/project/AMR/Handwriting/data")
    parser.add_argument('--dir',
                        type=str,
                        help="base directory to run job in (default tmp)")
    parser.add_argument('-b',
                        '--blame',
                        help="perform error blaming",
                        action="store_true")
    parser.add_argument('-t',
                        '--test',
                        help="only test given index in testset",
                        type=int)
    parser.add_argument('-p',
                        '--path',
                        help="generate viterbi path",
                        action="store_true")
    parser.add_argument('--janushome', default="/home/camma/svn/csl-ibis-amma")
    parser.add_argument(
        '--januscmd',
        default=
        "/home/camma/svn/csl-ibis-amma/src/Linux.i686-gcc-ltcl8.4-NX/janus")
    args = parser.parse_args()

    print()
    print("****** Starting BioKit Airwriting decoding with args:")
    pprint.pprint(args)
    print()

    janus_home = args.janushome
    janus_cmd = args.januscmd

    airdb = db.AirDb(args.database)
    config = airdb.session.query(
        db.Configuration).filter(db.Configuration.id == args.id).one()

    log("Info", "Using config:")
    pprint.pprint(config.__dict__)
    print()

    starttime = time.time()

    airrec = AirwritingRecognizer(airdb.session)
    if args.iter == 0 and config.basemodel:
        modelparam = config.basemodel
    else:
        modelparam = airdb.find_equal_training_modelsparameters(
            config, args.iter)
    log("Info", "Use models for iteration=%s: %s" % (args.iter, modelparam))
    airrec.setup(config, modelparam, args.dir)
    if args.test is None:
        resultslist = airrec.decode_set(config.testset, args.blame)
    else:
        resultslist = [
            airrec.decode(config.testset.recordings[args.test], args.blame,
                          args.path)
        ]
        vis.plot_path(airrec.path, airrec.searchGraphHandler.getSearchGraph(),
                      airrec.gmmScorer)
        vis.show()
    log("Info", str(resultslist))
    ter = align.totalTokenErrorRate(resultslist)
    log("Info", "Token Error Rate: " + str(ter))
    if args.blame:
        blamelog, confusionmap = airrec.getBlameResults()

    stoptime = time.time()
    duration = stoptime - starttime
    log("Info", "Duration: " + str(duration))

    print("****job finished")
    print("exit with return code 0")
    sys.exit(0)

import sys
import datetime

import unittest
import BioKIT

import os

sys.path.append("..")
import align

import pprint
import argparse
import visualization

if len(sys.argv) <= 1:
    outputfile = ''
else:
    outputfile = sys.argv[1]


def log(level, text):
    print "Python log: " + str(
        datetime.datetime.now()) + " - " + level + ": " + text


class AirwritingLoader:
    """
    Loads a BioKIT Airwriting recognizer from the description files present 
    in a given directory. Dictionary and grammar file can be given explicitly.
    
    The class is primarily intended to load an existing Recognizer created with
    Janus in a directory.
    """

    inputDataFileReader = BioKIT.InputDataFileReader()
    windowFramer = BioKIT.WindowFramer()
    averageCalculator = BioKIT.AverageExtractor()
    meanSubtraction = BioKIT.ZNormalization()
    channelRecombination = BioKIT.ChannelRecombination()

    def __init__(self, dictionary, grammarfile):

        log("Info", "Initializing Airwriting system from directory")

        log("Info", "Setting configuration parameters")

        gaussianContainerSet = BioKIT.GaussianContainerSet()
        gaussianContainerSet.readDescFile("gaussian_desc")
        gaussianContainerSet.loadDataFile("gaussian_data")

        log("Info", "Gaussian container set is: " + str(gaussianContainerSet))

        gaussMixtureSet = BioKIT.GaussMixturesSet(gaussianContainerSet)
        gaussMixtureSet.readDescFile("mixture_desc")
        gaussMixtureSet.loadDataFile("mixture_data")

        log("Info", "GaussMixtureSet is: " + str(gaussMixtureSet))

        self.gmmScorer = BioKIT.GmmFeatureVectorScorer(gaussMixtureSet)
        self.cacheScorer = BioKIT.CacheFeatureVectorScorer(self.gmmScorer)

        log("Info", "Generating model mapper")

        self.modelMapper = BioKIT.ModelMapper.ReadTopology(
            self.cacheScorer, "distrib_tree", "topology_tree", "topologies",
            "transitions")

        log("Info", "Loading atoms from janus phonesSet")
        atomMap = BioKIT.AtomManager()
        atomMap.readAtomManager("phones")

        log("Info", "Loading dictionary")
        self.dictionary = BioKIT.Dictionary(atomMap)
        if dictionary:
            self.dictionary.readDictionary(dictionary)
        else:
            self.dictionary.readDictionary("dict")
        self.dictionary.config().setStartToken("<s>")
        self.dictionary.config().setEndToken("</s>")
        self.dictionary.config().setUnknownToken("<UNK>")

        log("Info", "Dictionary tokens:")

        tokens = self.dictionary.getTokenList()
        for t in tokens:
            log("Trace", str(t))

        log("Info", "Generating search vocabulary from dictionary")

        self.vocabulary = BioKIT.SearchVocabulary(self.dictionary)

        #log("Info", "Creating 0-gram tokensequence model")
        #tokenSequenceModel = BioKIT.ZeroGram(dictionary)

        log("Info", "Creating grammar tokensequence model")
        grammar = BioKIT.GrammarTokenSequenceModel(self.dictionary)
        if grammarfile:
            grammar.readSimplifiedGrammar(grammarfile)
        else:
            grammar.readSimplifiedGrammar("grammar.new")

        #nt0 = grammar.addNonTerminalNode("nt0")
        #nt0_0 = grammar.setStartSymbol(nt0)
        #allowedTokens =  [dictionary.getTokenIds(chr(i))[0] for i in range(ord('a'), ord('z')+1)]
        #allowedWords = [dictionary.getTokenId("can")]
        #for token in allowedTokens:
        #    log("Info", "creating terminal node for " + dictionary.getToken(token))
        #    nodeId = grammar.addTerminalNode(token)
        #    log("Info", "adding edge from " + str(nt0) + " to " + str(nodeId))
        #    grammar.addSuccessor(nt0, nodeId)
        #    log("Info", "set " + str(nodeId) + " as end node" )
        #    grammar.setEndNode(nodeId)

        self.tokenSequenceModel = grammar

        #log('info', 'Creating tokensequence model with fillers')
        #self.tokenSequenceModel = BioKIT.FillerWrapper(self.tokenSequenceModel, self.dictionary, 'FILLER')

        #log("Info", "building atom HMMs")
        #atomMap = dictionary.getAtomManager()

        log("Info", "Making search graph")

        self.hypoBeam = 100000
        self.hypoTopN = 100000
        self.activeNodeBeam = 100000
        self.activeNodeTopN = 200000
        self.finalNodeBeam = 100000
        self.finalNodeTopN = 100000
        self.beams = BioKIT.Beams(self.hypoBeam, self.hypoTopN,
                                  self.activeNodeBeam, self.activeNodeTopN,
                                  self.finalNodeBeam, self.finalNodeTopN)
        self.tokenSequenceModelWeight = 0
        self.tokenInsertionPenalty = 50.0
        # free search
        self.searchGraphHandler = BioKIT.SearchGraphHandler(
            self.tokenSequenceModel, self.dictionary, self.vocabulary,
            self.modelMapper, self.cacheScorer, self.beams,
            self.tokenSequenceModelWeight, self.tokenInsertionPenalty)
        self.searchGraphHandler.setKeepHyposAlive(True)
        self.searchGraphHandler.createDotGraph("searchgraph.dot")
        self.decoder = BioKIT.Decoder(self.searchGraphHandler)

    def preprocessing(self, adcPath):
        samplingRate = 819
        adcOffset = 0
        numChannels = 7
        frameLength = int(samplingRate * 0.01)
        frameShift = 0
        log("Info", "Preprocessing " + adcPath)
        data = self.inputDataFileReader.readFile(
            adcPath, BioKIT.SF_FORMAT.RAW | BioKIT.SF_FORMAT.PCM_16,
            samplingRate, numChannels, 0, 0, adcOffset)
        #delete first channel which contains the counter
        del data[0]
        data = self.windowFramer.applyWindow(data, frameLength, frameShift,
                                             BioKIT.WindowType.rectangular)
        data = self.averageCalculator.calculateFrameBasedAverage(data)
        self.meanSubtraction.resetMeans()
        self.meanSubtraction.updateMeans(data, 1.0, True)
        data = self.meanSubtraction.subtractMeans(data, 1.0)
        data = self.channelRecombination.performFeatureFusion(data)
        featureSequence = data[0]
        return featureSequence

    def forcedAlignment(self, mcfs, reference):
        # constrained search (forced alignment)
        tokens = reference.split()
        tokenids = [self.dictionary.getBaseFormId(x) for x in tokens]
        print("tokenids: %s" % tokenids)
        sil = self.dictionary.getBaseFormId("SIL")
        print("filler: %s" % sil)
        self.utteranceSearchGraphHandler = BioKIT.SearchGraphHandler(
            self.dictionary, tokenids, sil, self.modelMapper, self.cacheScorer,
            self.beams, self.tokenSequenceModelWeight,
            self.tokenInsertionPenalty)
        print("Search graph constructed")
        self.utteranceSearchGraphHandler.setKeepHyposAlive(True)
        self.utterancedecoder = BioKIT.Decoder(
            self.utteranceSearchGraphHandler)
        print("perform forced alignment")
        self.utterancedecoder.search(multiChannel, True)
        #forcedresults = self.decoder.extractSearchResult()
        forcedpath = self.utterancedecoder.traceViterbiPath()
        print("**** forced path scores *****")
        nodeIds = [forcedpath[i].mNodeId for i in range(len(forcedpath))]
        print(nodeIds)
        uniqNodeIds = sorted(list(set(nodeIds)))
        modelNames = [
            self.cacheScorer.getModelName(
                self.utteranceSearchGraphHandler.getSearchGraph().getNode(
                    nid).getModelId()) for nid in uniqNodeIds
        ]
        mappedNodeIds = [uniqNodeIds.index(i) for i in nodeIds]
        for pi in forcedpath:
            print("modelId: %s , partialScore: %s" %
                  (pi.mModelId, pi.mPartialScore))
        plotpath = visualization.PlotPath(
            forcedpath, multiChannel[0],
            self.utteranceSearchGraphHandler.getSearchGraph(), self.gmmScorer)
        plotpath.plot("forces alignment")
        visualization.show()

    def search(self, adcPath, reference):

        featSeq = BioKIT.FeatureSequence()
        print("preprocessing")
        featSeq = self.preprocessing(os.path.join(adcPath))
        multiChannel = BioKIT.MultiChannelFeatureSequence()
        multiChannel.append(featSeq)
        visualization.plot_mcfs(multiChannel)
        visualization.show()
        #self.forcedAlignment(multiChannel, reference)

        log("Info", "Creating BioKIT")
        self.decoder.search(multiChannel, True)
        results = self.decoder.extractSearchResult()
        print(results)
        path = self.Decoder.traceViterbiPath()
        for res in results:
            print("hypo: %s, score: %s" % (res.toString(), res.score))
        plotpath = visualization.PlotPath(
            path, multiChannel[0], self.searchGraphHandler.getSearchGraph(),
            self.gmmScorer)
        plotpath.plot("free decoding")
        visualization.show()


if __name__ == '__main__':
    # workaround to get verbose output, it's better in Python 2.7
    #myArgv = sys.argv[0:1] + ["-v"]
    parser = argparse.ArgumentParser(
        description="Load Airwriting system from" + " description files")
    parser.add_argument('input', help="input adc file to decode")
    parser.add_argument('reference', help="reference for given input")
    parser.add_argument('-d', '--dictionary', help="dictionary file")
    parser.add_argument('-g', '--grammar', help='grammar file')
    args = parser.parse_args()

    airloader = AirwritingLoader(args.dictionary, args.grammar)
    airloader.search(args.input, args.reference)

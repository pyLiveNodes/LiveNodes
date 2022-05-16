import sys
import unittest

import os

import BioKIT

import string
import re  #regular expressions
import filecmp  #file comparison
import os
import glob
import sqlite3

import datetime

sys.path.append("../../python-lib")
import align
import vtln
import matrix

import BioKIT
from BioKIT import *
import preprocessingChain


# TODO: think about logging in Python
def log(level, text):
    print("Python log: " + str(datetime.datetime.now()) + " - " + level +
          ": " + text)


class TestIntegrationTestSpeech(unittest.TestCase):
    inputDataFileReader = InputDataFileReader()
    windowFramer = WindowFramer()
    spectrumCalculator = SpectrumExtractor()
    melFilter = MelFilter()
    logApplier = LogarithmApplier()
    dctTransformer = DiscreteCosineTransformer()
    meanSubtraction = ZNormalization()
    adjacentStacking = AdjacentStacking()
    ldaTransform = LinearTransform()

    def test_allTestData(self):
        samplingRate = 16000
        frameLength = int(samplingRate * 0.016)
        overlap = int(samplingRate * 0.006)
        windowType = WindowType.hamming
        numMelCoefficients = 30
        lowFreq = 0
        highFreq = samplingRate / 2
        numDctCoefficients = 13

        logK = 1
        logA = 1
        meanSubA = 2
        adjacentStackingDelta = 5

        #topN hypos to keep in snapshot after decoding
        topNHypoSnapshots = 100

        snappath = "/data/tmp"
        #path to the reference snapshots
        refSnapshotPath = os.path.join(snappath, "GPEN-refSnaps2")

        #path to the hypo snapshots
        hypoSnapshotPath = os.path.join(snappath, "GPEN-shrunkSnaps")

        #path to temporary snapshot file before shrinking
        tmpSnapshot = os.path.join(snappath, "GPEN-shrunkSnaps/tmp.snp")

        pre_processing_chain_before_mel = preprocessingChain.PreprocessingChain(
        )
        pre_processing_chain_from_mel = preprocessingChain.PreprocessingChain()

        def init_pre_processing_chains():
            pre_processing_chain_before_mel.addOperator(
                self.windowFramer.applyWindow, frameLength, overlap,
                windowType)
            pre_processing_chain_before_mel.addOperator(
                self.spectrumCalculator.calculateRealPowerSpectrogram)
            #pre_processing_chain_from_mel.addOperator(self.melFilter.applyMelFilterbank, samplingRate, numMelCoefficients, lowFreq, highFreq, "vtlnWarpingFactor") # this sets the warping factor to be replaced by a value when  pre_processing_chain_from_mel.execute() is executed
            pre_processing_chain_from_mel.addOperator(
                self.melFilter.applyMelFilterbank,
                samplingRate,
                numMelCoefficients,
                lowFreq,
                highFreq,
                "vtlnWarpingFactor",
                False,  # janus model
                True
            )  # this sets the warping factor to be replaced by a value when  pre_processing_chain_from_mel.execute() is executed
            pre_processing_chain_from_mel.addOperator(self.logApplier.applyLog,
                                                      logK, logA)
            pre_processing_chain_from_mel.addOperator(
                self.dctTransformer.calculateDct, numDctCoefficients)
            pre_processing_chain_from_mel.addOperator(
                self.meanSubtraction.subtractMeans, meanSubA)
            pre_processing_chain_from_mel.addOperator(
                self.adjacentStacking.stackAdjacentFeatureVectors,
                adjacentStackingDelta)
            pre_processing_chain_from_mel.addOperator(
                self.ldaTransform.calculateLinearTransform)

        def pre_processing(adcPath, vtlnParam=1.0):
            log("Info", "Preprocessing " + adcPath)
            numChannels = 1
            adcOffset = -1
            mcfs1 = self.inputDataFileReader.readFile(
                adcPath, SF_FORMAT.RAW | SF_FORMAT.PCM_16, samplingRate,
                numChannels, adcOffset)
            mcfs1 = pre_processing_chain_before_mel.execute(mcfs1)
            mcfs2 = pre_processing_chain_from_mel.execute(
                mcfs1, vtlnWarpingFactor=vtlnParam)
            return (mcfs1, mcfs2)

        log("Info", "Starting test_allTestData")
        # define parameters for database
        pathPrefix = "/home"
        dataSpeechPath = '../../integration_test/_dataSpeech/'
        databasePath = '/home/telaar/db.newDecoderRelativePaths/speech.db'
        log("Info", databasePath)

        tableName = 'TestData'
        # spkeaker list
        spkLst = dataSpeechPath + 'spkLst.test'

        log("Info", "Initialize Pre-processing")

        ldaMatrix = matrix.loadFloatMatrix(dataSpeechPath +
                                           "_cd/ldaCSLcd.bmat")
        ldaMatrix = ldaMatrix.transpose()
        # saves transposed LDA matrices
        self.ldaTransform.setTransformationMatrix(ldaMatrix)
        numLdaCoefficients = 42
        self.ldaTransform.cutTransformationMatrix(numLdaCoefficients)
        #cutoff dimensionality for lda

        gaussianContainerSet = GaussianContainerSet()
        gaussianContainerSet.readDescFile(dataSpeechPath + "_cd/mas.cbsDesc")
        gaussianContainerSet.loadDataFile(dataSpeechPath + "_cd/6.cbs")

        gaussMixturesSet = GaussMixturesSet(gaussianContainerSet)
        gaussMixturesSet.readDescFile(dataSpeechPath + "_cd/mas.dssDesc")
        gaussMixturesSet.loadDataFile(dataSpeechPath + "_cd/6.dss")

        gmmScorer = GmmFeatureVectorScorer(gaussMixturesSet)
        cacheScorer = CacheFeatureVectorScorer(gmmScorer)

        log("Info", "Loading phones set")
        atomMap = AtomManager()
        atomMap.readAtomManager(dataSpeechPath + "_cd/ENphonesSet")

        log("Info", "Loading dictionary")

        dictionary = Dictionary(atomMap)
        dictionary.registerAttributeHandler('FILLER', NumericValueHandler())
        dictionary.registerAttributeHandler('SILENCE', NothingHandler())
        dictionary.registerAttributeHandler('TOKEN_SCORE',
                                            NumericValueHandler())
        dictionary.config().setStartToken("<s>")
        dictionary.config().setEndToken("</s>")
        dictionary.config().setUnknownToken("<UNK>")
        dictionary.readDictionary(dataSpeechPath + "_dict/dictionary")

        log("Info", "Generating model mapper")

        modelMapper = ModelMapper.ReadTopology(
            cacheScorer, atomMap, dataSpeechPath + "_cd/ENdistribTree.2000p",
            dataSpeechPath + "topologyTree", dataSpeechPath + "topologies",
            dataSpeechPath + "transitionModels")

        vocabulary = SearchVocabulary(dictionary)

        log("Info", "Creating tokensequence model")
        tokenSequenceModel = NGram(dictionary)
        tokenSequenceModel.readArpaFile(
            dataSpeechPath + "_lm/English3k.trigram.lm", vocabulary)

        log('info', 'Creating tokensequence model with fillers')
        fillerWrapper = FillerWrapper(tokenSequenceModel, dictionary, 'FILLER')

        cacheTsm = CacheTokenSequenceModel(fillerWrapper, dictionary)

        log("Info", "Dictionary tokens:")

        tokens = dictionary.getTokenList()
        #for t in tokens:
        #    log("Trace",str(t))

        log("Info", "building atom HMMs")
        atomMap = dictionary.getAtomManager()

        log("Info", "Making search graph handler")
        hypoBeam = 60
        hypoTopN = 10
        activeNodeBeam = 250
        activeNodeTopN = 8000
        finalNodeBeam = 120
        finalNodeTopN = 50
        beams = BioKIT.Beams(hypoBeam, hypoTopN, activeNodeBeam,
                             activeNodeTopN, finalNodeBeam, finalNodeTopN)
        tokenSequenceModelWeight = 26.0
        tsmLaTokenSequenceModelWeight = 26.0
        tsmlaCacheSize = 1000
        tokenInsertionPenalty = 0.0
        maxLMLATreeDepth = -1
        #important to keep parameter at -1
        searchGraphHandler = SearchGraphHandler(cacheTsm, dictionary,
                                                vocabulary, modelMapper,
                                                cacheScorer, beams,
                                                tokenSequenceModelWeight,
                                                tokenInsertionPenalty)
        searchGraphHandler.setKeepHyposAlive(True)

        # create LMLA structure, using the main tokensequence model
        log("Info", "Creating tokensequence model lookahead")

        cacheTsm.config().setMaxScoreCache(tsmlaCacheSize)
        searchGraphHandler.createTsmLookAhead(maxLMLATreeDepth)
        searchGraphHandler.getTsmLookAhead().config().setTsmWeight(
            tsmLaTokenSequenceModelWeight)
        searchGraphHandler.getTsmLookAhead().config().setMaxNodeCache(
            tsmlaCacheSize)

        log("Info", "Creating BioKIT")
        decoder = Decoder(searchGraphHandler)

        log("Info", "Initializing preprocessing")
        init_pre_processing_chains()

        # connect to the database and get info
        database = sqlite3.connect(databasePath)
        database.row_factory = sqlite3.Row
        database.text_factory = str
        database_cursor = database.cursor()

        # initialize total words, sub, ins and del
        totalWords = 0
        totalSub = 0
        totalIns = 0
        totalDel = 0

        for spkId in open(spkLst):
            spkId = spkId.replace("\n", "")
            sqlcmd = "SELECT * FROM " + tableName + " WHERE SPKID = " + spkId
            print("Now we do " + sqlcmd)
            database_cursor.execute(sqlcmd)
            infos = database_cursor.fetchall()
            self.meanSubtraction.loadMeans(
                dataSpeechPath + '_prepro/' + spkId + '.mean',
                dataSpeechPath + '_prepro/' + spkId + '.smean')

            for info in infos:
                log("Info", "Will try to create Snapshot now")
                snapshotName = os.path.join(hypoSnapshotPath,
                                            str(info['UTTID']) + ".snp")
                refsnapName = os.path.join(refSnapshotPath,
                                           str(info['UTTID']) + ".snp")

                if os.path.exists(
                        refsnapName) and not os.path.exists(snapshotName):
                    searchGraphHandler.createSnapshot(
                        tmpSnapshot, tokenSequenceModelWeight,
                        tokenInsertionPenalty)
                    log("Info", "created Snapshot file")

                    adcPath = os.path.join(pathPrefix, info['ADC'])
                    adcPath = os.path.normpath(adcPath)

                    featSeq = pre_processing(
                        adcPath
                    )[1]  # 0 = after MEL; 0 = first entry (there should only be one)
                    decoder.search(featSeq, True)
                    results = decoder.extractSearchResult()

                    reference = info['TEXT']
                    print(reference)
                    if len(results) == 0:
                        resultFile.write("\n")
                        continue

                    log("Info", "results:")
                    log("Info",
                        results[0].toString() + " " + str(results[0].score))

                    resultString = results[0].toString()
                    # now remove silences from the resulting string
                    cleanedString = resultString.replace("$", "").rstrip()
                    cleanedString = cleanedString.replace("#noise#",
                                                          "").rstrip()
                    cleanedString = cleanedString.lstrip()
                    # map search result to base form
                    tokenList = [
                        dictionary.getBaseForm(token)
                        for token in cleanedString.split()
                    ]
                    cleanedString = ' '.join(t for t in tokenList)

                    log("Info", "cleaned hypo is: " + cleanedString)

                    log("Info", "reference is: " + reference)

                    # get sub, ins and del
                    tokenErrorInfo = align.tokenErrorRateInsDelSubCount(
                        reference, cleanedString)
                    sub = tokenErrorInfo[0][3]
                    ins = tokenErrorInfo[0][1]
                    delete = tokenErrorInfo[0][2]
                    words = len(reference.split())
                    tokenErrorRate = float(sub + ins + delete) / words
                    log(
                        "Info", "Token error information: SPKID: " +
                        str(spkId) + " UTT: " + str(info['UTT']) + " SUB: " +
                        str(sub) + ", INS: " + str(ins) + ", DEL: " +
                        str(delete) + ", WER: " + str(tokenErrorRate))

                    totalWords += words
                    totalSub += sub
                    totalIns += ins
                    totalDel += delete

                    SnapshotHandler.Shrink(tmpSnapshot, topNHypoSnapshots,
                                           snapshotName)
                else:
                    print((
                        "no reference snapshot available or hypo snapshot already existing: %s"
                        % refsnapName))

        averageTokenErrorRate = float(totalSub + totalIns +
                                      totalDel) / totalWords
        log(
            "Info", "Average token error rate (without VTLN) is: " +
            str(averageTokenErrorRate))
        log(
            "Info", "Token error information (without VTLN): SUB: " +
            str(totalSub) + ", INS: " + str(totalIns) + ", DEL: " +
            str(totalDel) + ", Total Words: " + str(totalWords))


if __name__ == '__main__':
    runner = unittest.TextTestRunner

    unittest.main('__main__', None, myArgv, runner)

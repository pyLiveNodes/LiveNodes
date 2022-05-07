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

        #try different factors for beams if a path cannot be traced
        beamFactor = 1

        #number the current beam factor is multiplied with to get the next beam factor
        beamStep = 2

        #maximum beam factor allowed before skipping the utterance completely
        beamMax = 8

        #path to store the reference snapshots in
        refSnapshotPath = "/data/tmp/GPEN-refSnaps2"

        logK = 1
        logA = 1
        meanSubA = 2
        adjacentStackingDelta = 5

        pre_processing_chain_before_mel = preprocessingChain.PreprocessingChain(
        )
        pre_processing_chain_from_mel = preprocessingChain.PreprocessingChain()

        #def init_pre_processing_chains(mcfs):

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

        dataSpeechPath = '../../integration_test/_dataSpeech/'

        log("Info", "Starting test_allTestData")
        # define parameters for database
        pathPrefix = "/home"
        databasePath = os.path.join(
            pathPrefix, 'telaar/db.newDecoderRelativePaths/speech.db')
        databasePath = os.path.normpath(databasePath)

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

        log("Info", "building atom HMMs")
        atomMap = dictionary.getAtomManager()

        log("Info", "Making search graph handler")
        hypoBeam = 150
        hypoTopN = 30
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

        log("Info", "Initializing preprocessing")
        init_pre_processing_chains()

        # connect to the database and get info
        print(databasePath)
        database = sqlite3.connect(databasePath)
        database.row_factory = sqlite3.Row
        database.text_factory = str
        database_cursor = database.cursor()

        for spkId in open(spkLst):
            spkId = spkId.replace("\n", "")
            sqlcmd = "SELECT * FROM " + tableName + " WHERE SPKID = " + spkId
            print("Now we do " + sqlcmd)
            database_cursor.execute(sqlcmd)
            infos = database_cursor.fetchall()
            self.meanSubtraction.loadMeans(
                dataSpeechPath + '_prepro/' + spkId + '.mean',
                dataSpeechPath + '_prepro/' + spkId + '.smean')

            infoList = []
            for info in infos:
                infoList.append(info)

            i = 0
            while (i < len(infoList)):
                info = infoList[i]
                adcPath = os.path.join(pathPrefix, info['ADC'])
                adcPath = os.path.normpath(adcPath)

                skipUtterance = False
                reference = info['TEXT']

                tokens = reference.split()
                tokenIds = []
                for token in tokens:
                    tokenId = dictionary.getBaseFormId(token)

                    if (tokenId == -1):
                        skipUtterance = True
                        log("Info",
                            "Skipped utterance, because of invalid token")
                        break
                    tokenIds.append(tokenId)

                if (skipUtterance != True):
                    searchGraphHandler = SearchGraphHandler(
                        dictionary, tokenIds, dictionary.getBaseFormId("$"),
                        modelMapper, cacheScorer, beams,
                        tokenSequenceModelWeight, tokenInsertionPenalty)

                    searchGraphHandler.setTokenSequenceModel(cacheTsm)

                    log("Info", "Creating BioKIT")
                    decoder = Decoder(searchGraphHandler)

                    searchGraphHandler.setKeepHyposAlive(True)

                    log("Info", "Will try to create Snapshot now")
                    snapshotName = refSnapshotPath + "/" + str(
                        info['UTTID']) + ".snp"
                    searchGraphHandler.createSnapshot(
                        snapshotName, tokenSequenceModelWeight,
                        tokenInsertionPenalty)
                    log("Info", "created Snapshot file")

                    if (os.path.isfile(adcPath) != True):
                        log("Warning",
                            "File " + info['ADC'] + "does not exist!")
                    else:
                        featSeq = pre_processing(
                            adcPath
                        )[1]  # 0 = after MEL; 0 = first entry (there should only be one)
                        decoder.search(featSeq, True)

                        result = decoder.extractSearchResult()
                        #test if we have a result
                        if (len(result) == 0):
                            #increase beam size and redo utterance
                            beamFactor = beamStep * beamFactor
                            if (beamFactor > beamMax):
                                beamFactor = 1
                                skipUtterance = True
                                os.remove(snapshotName)
                                log(
                                    "Info",
                                    "Skipping utterance, deleting reference snapshot file"
                                )
                            else:
                                i = i - 1
                                #decrement i to redo the utterance
                                log(
                                    "Info", "Increasing beam factor to " +
                                    str(beamFactor))
                i = i + 1
                #increment i for next utterance


if __name__ == '__main__':
    runner = unittest.TextTestRunner

    unittest.main('__main__', None, myArgv, runner)

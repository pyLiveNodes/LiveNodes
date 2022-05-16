# -*- coding: utf-8 -*-
import sys
import unittest

import BioKIT

import string
import re  #regular expressions
import filecmp  #file comparison
import os
import glob

import datetime

sys.path.append("../../python-lib")
import align
import vtln

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

    log("Info", "Starting test_allTestData")
    # define parameters for database
    databasePath = '/home/erhardt/c++workspace/decoder-data/codeSwitch.db'
    tableName = 'CodeSwitchData'
    # spkeaker list
    spkLst = '/home/erhardt/c++workspace/decoder-data/spkLst'

    database = BioKIT.Database()
    database.openSQLiteDb(databasePath, BioKIT.Database.CreateNonexisting)

    for spkId in open(spkLst):
        spkId = spkId.replace("\n", "")
        sqlcmd = "SELECT * FROM " + tableName + " WHERE SPKID = '" + spkId + "'"
        print("Now we do " + sqlcmd)
        infos = database.executeStatement(sqlcmd)
        i = 0

        infoList = []
        for info in infos:
            infoList.append(info)

        while i < len(infoList):
            info = infoList[i]
            # create Snapshot structure
            log("Info", "Will try to create Snapshot now")
            sourceSnapshot = "/data/erhardt/SEAME-snaps/" + str(
                info['UTTID']) + ".snp"
            shrunkSnapshot = "/data/erhardt/SEAME-shrunkSnaps/" + str(
                info['UTTID']) + ".snp"

            if not os.path.exists(sourceSnapshot):
                i = i + 1  # no source file exists, continue with next

            else:
                SnapshotHandler.shrink(sourceSnapshot, 100, shrunkSnapshot)
                i = i + 1
                #increment i for next utterance


if __name__ == '__main__':
    runner = unittest.TextTestRunner

    unittest.main('__main__', None, myArgv, runner)

# -*- coding: utf-8 -*-
import sys
import unittest

import BioKIT

import string
import re  #regular expressions
import filecmp  #file comparison
import os
import ast
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


databasePath = '/home/erhardt/c++workspace/decoder-data/codeSwitch.db'
tableName = 'CodeSwitchData'

# connect to the database and get info
database = BioKIT.Database()
database.openSQLiteDb(databasePath, BioKIT.Database.CreateNonexisting)

# definition of paths
referencesPath = "/data/erhardt/SEAME-refSnaps/"
snapshotsPath = "/data/erhardt/SEAME-shrunkSnaps/"
resultPath = "/project/ASR/erhardt/confusionResults/"

gaussianContainerSet = GaussianContainerSet()
gaussianContainerSet.readDescFile(
    "/home/erhardt/c++workspace/decoder-data/Weights/mas.cbsDesc")
gaussianContainerSet.loadDataFile(
    "/home/erhardt/c++workspace/decoder-data/Weights/6.cbs")

log("Info", "Gaussian container set is: " + str(gaussianContainerSet))
gaussMixturesSet = GaussMixturesSet(gaussianContainerSet)
gaussMixturesSet.readDescFile(
    "/home/erhardt/c++workspace/decoder-data/Weights/mas.dssDesc")
gaussMixturesSet.loadDataFile(
    "/home/erhardt/c++workspace/decoder-data/Weights/6.dss")

log("Info", "GaussMixturesSet is: " + str(gaussMixturesSet))

gmmScorer = GmmFeatureVectorScorer(gaussMixturesSet)
cacheScorer = CacheFeatureVectorScorer(gmmScorer)

sqlcmd = "SELECT * FROM " + tableName
print("Now we do " + sqlcmd)
infos = database.executeStatement(sqlcmd)
infoList = []
for info in infos:
    infoList.append(info)

confusionHandler = ConfusionHandler(cacheScorer)
i = 0
while i < len(infoList):
    info = infoList[i]

    if (os.path.exists(referencesPath + str(info['UTTID']) + ".snp")
            and os.path.exists(snapshotsPath + str(info['UTTID']) + ".snp")):
        log("Info",
            "Utterance " + str(info['UTTID']) + " has complete dataset.")
        log("Info", "Importing referenceFile")
        refFile = (referencesPath + str(info['UTTID']) + ".snp")

        snapshotFile = (snapshotsPath + str(info['UTTID']) + ".snp")

        log("Info", "Now collecting confusions")
        confusionHandler.collectConfusions(snapshotFile, refFile)
        log("Info", "Collected Confusions for " + str(info['UTTID']))

    else:
        log("Info",
            "Utterance " + str(info['UTTID']) + " is incomplete. Skipping...")
    i = i + 1
resultFile = open(
    resultPath + "SEAME-confusionTable-" +
    str(datetime.datetime.today().isoformat()) + ".csv", 'w')
resultFile.write(confusionHandler.toCSV())

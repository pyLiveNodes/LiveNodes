# -*- coding: utf-8 -*-
import sys
import unittest

import string
import re           #regular expressions
import filecmp      #file comparison
import os
import ast
import glob
import sqlite3
import datetime

sys.path.append("../../python-lib")
import align
import vtln

import BioKIT
from BioKIT import *
import preprocessingChain

#####################################
########### CONFIGURATION ###########
#####################################
# set outputfile to something if you want XML output
# set it to '' if you want text output
#outputfile = 'BioKIT_IntegrationTestSpeech_Result.xml'
#outputfile = ''
if len(sys.argv) <= 1:
    outputfile = ''
else:
    outputfile = sys.argv[1]
#outputfile = sys.argv[1]
#####################################

# TODO: think about logging in Python
def log(level,text):
	print("Python log: " + str(datetime.datetime.now()) + " - " + level + ": " + text)

pathPrefix = "/home"
dataSpeechPath = '../../integration_test/_dataSpeech/'
databasePath = '/home/telaar/db.newDecoderRelativePaths/speech.db'
tableName = 'TestData'

 # connect to the database and get info
database = sqlite3.connect(databasePath)
database.row_factory = sqlite3.Row
database.text_factory = str
database_cursor = database.cursor()

# load Dictionary for token information
atomMap = AtomManager()
atomMap.readAtomManager(dataSpeechPath + "_cd/ENphonesSet")

# Create Abstract Feature Vector Scorer
gaussianContainerSet = GaussianContainerSet()
gaussianContainerSet.readDescFile(dataSpeechPath + "_cd/mas.cbsDesc")
gaussianContainerSet.loadDataFile(dataSpeechPath + "_cd/6.cbs")

gaussMixturesSet = GaussMixturesSet(gaussianContainerSet)
gaussMixturesSet.readDescFile(dataSpeechPath + "_cd/mas.dssDesc")
gaussMixturesSet.loadDataFile(dataSpeechPath + "_cd/6.dss")

gmmScorer = GmmFeatureVectorScorer(gaussMixturesSet)
cacheScorer = CacheFeatureVectorScorer(gmmScorer)

log("Info","Loading dictionary")

dictionary = Dictionary(atomMap)
dictionary.registerAttributeHandler('FILLER', NumericValueHandler())
dictionary.registerAttributeHandler('SILENCE', NothingHandler())
dictionary.registerAttributeHandler('TOKEN_SCORE', NumericValueHandler())
dictionary.config().setStartToken("<s>")
dictionary.config().setEndToken("</s>")
dictionary.config().setUnknownToken("<UNK>")
dictionary.readDictionary(dataSpeechPath + "_dict/dictionary");

# creation of ErrorBlamer
errorBlamer = ErrorBlamer(dictionary, 0.7, cacheScorer)

# path to reference snapshots
referencesPath = "/data/tmp/GPEN-refSnaps2/"

#path to the hypo snapshots
snapshotsPath = "/data/tmp/GPEN-shrunkSnaps/"

#path to write blaming to
blameResultsPath = "/data/tmp/GPEN-blameResults/"

# blameLog
blameLog = open(blameResultsPath + "GPEN-blameLog-70-shrunk" + str(datetime.datetime.today().isoformat()) + ".csv", 'w')

sqlcmd ="SELECT * FROM " + tableName
print("Now we do " + sqlcmd)
database_cursor.execute(sqlcmd)
infos = database_cursor.fetchall()
for info in infos:
	if(os.path.exists(referencesPath + str(info['UTTID'])+ ".snp") and os.path.exists(snapshotsPath + str(info['UTTID']) + ".snp")):
		log("Info","Utterance "+ str(info['UTTID']) + " has complete dataset: Importing snapshots.")
		refFile = (referencesPath + str(info['UTTID']) + ".snp")
		snapshotFile = (snapshotsPath + str(info['UTTID']) + ".snp")
		errorBlamer.loadSnapshots(snapshotFile,refFile)
		log("Info","Finished loading Snapshots")

		blameLog.write("Blame assignment for " + str(info['UTTID']) + ":\n")
		blameLog.write(errorBlamer.blameAndWriteUtterance() + "\n\n")

	else:
		log("Info","Utterance "+ str(info['UTTID']) + " is incomplete. Skipping...")

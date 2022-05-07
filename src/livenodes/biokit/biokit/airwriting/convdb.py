# coding: utf-8
import sys

sys.path.append("airwriting")
from . import db
from . import AirwritingDb
"""
This script converts the old style recording databased to the new style format
with all different recording types in one big database

the source databases can either be given as plain csv files or as sql databases
with only one flat table containing all the recordings. The format of the csv
file must be key,value,key,value,.... it can be generated from old style 
databases with the tcl script convertDB.tcl
"""

#convert_chardata = True
#convert_worddata = True
#convert_sendata = True
convert_waxdata = True

#targetdb = "/mnt/sdb2/data/tmp/airwriting_dev_char.sqlite"
#targetdb = "/project/AMR/Handwriting/data/db/airwriting_dev_char.sqlite"
targetdb = "mysql+mysqldb://@i19pc56/diss"
chardb_path = "/project/AMR/Handwriting/data/db/all.sqlite"
#worddb_path = "/home/camma/workspace/decoder/python/integration_test/_simple/_dataAirwriting/airwritingWords.sqlite"
worddb_path = "/project/AMR/Handwriting/data/db/airwriting_dev_word.jdb.sqlite"
worddb_csv = "/project/AMR/Handwriting/data/db/db_tmp.csv"
sendb_path = "/home/camma/tools/ci/workspace/decoder/python/integration_test/_simple/_dataAirwriting/airwritingSentences.sqlite"
senwithwaxdb_path = "/project/AMR/Handwriting/data/db/dev.sentences.transform.multiple.sqlite"

airdb = db.AirDb(targetdb)

# load the different databases and convert to new format
if convert_chardata:
    janusdb = db.JanusDb(chardb_path)
    janusdb.insert_into_airdb(airdb, 'character')

#load the word recordings
#the database does not contain janus ids, so the method below should be used
#if convert_worddata:
#    wordb = AirwritingDb.AirwritingDb()
#    wordb.open(worddb_path)
#    wordb.convertToNewDb(targetdb)

#load word recordings from csv
if convert_worddata:
    wordjanusdb = db.JanusDb(worddb_path)
    #    with open(worddb_csv, "r") as fh:
    #        wordjanusdb.insert_from_csv(fh, "")
    wordjanusdb.insert_into_airdb(airdb, 'word')

#load the sentence recordings
if convert_sendata:
    sendb = AirwritingDb.AirwritingDb(senwithwaxdb_path)

    sendb.convertToNewDb(targetdb,
                         has_corrupt_rec=True,
                         use_id_as_janusid=True)

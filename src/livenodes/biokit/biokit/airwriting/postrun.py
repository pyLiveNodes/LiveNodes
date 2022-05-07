#!/usr/bin/python
import sys

sys.path.append("/home/camma/tools/ci/workspace/decoder/python/python-lib")

import pickle

# python-lib
import align
from . import AirwritingDb
from . import airwritingUtil

tablecvfolds = "evalBioKit"
foldnr = 9


def postrun(results,
            config,
            database,
            resulttable,
            foldNr,
            refkey="reference",
            hypokey="hypothesis"):

    if results:
        wer = align.totalTokenErrorRate(results, refkey, hypokey)
        config['wer'] = wer
        print("WER: " + str(wer))

    db = AirwritingDb.AirwritingDb()
    print("open database " + database)
    db.open(database)

    print("insert config and results into database")
    resultview = "view" + resulttable

    config.generateConfigTable(db, resulttable)
    #db.createViewCVResults(resulttable, resultview, foldnr,
    #                       groupby = "expId, nriter")
    config.insertIntoDb(db, resulttable)
    db.close()


if __name__ == "__main__":

    ##### currently broken

    #parser = argparse.ArgumentParser(description="Run post action after one"
    #                                 + " recognizer run")
    #parser.add_argument('file', help="result csv file to process")
    #parser.add_argument('config', help="pickled config file with parameters")
    #parser.add_argument('database', help="sqlite database file for storing results")
    #parser.add_argument('resulttable')
    #parser.add_argument('resultview')
    #parser.add_argument('foldNr', help="number of cross-validation folds")
    #parser.add_argument('--config-param', dest = 'configParam',  nargs = 2,
    #                    action = 'append', help="additional config parameter")
    #args = parser.parse_args()

    print("reading result file " + args.file)
    with open(args.file, "r") as fh:
        results = airwritingUtil.readResultFile(fh)

    print("reading config object from " + args.config)
    with open(args.config, "r") as fh:
        config = pickle.load(fh)
    for k in config:
        print(k)

    print("additional key, value pairs: " + str(args.configParam))
    if args.configParam:
        for paramPair in args.configParam:
            print("set " + paramPair[0] + " to " + paramPair[1])
            config[paramPair[0]] = paramPair[1]

    print(results)
    postrun(results, config, args.database)

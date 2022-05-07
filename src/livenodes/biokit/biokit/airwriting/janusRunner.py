import argparse
import pprint
import tempfile
import subprocess
import os
import socket
import shutil
import Database
from . import airwritingConfig
from . import airwritingUtil
from . import postrun
import time
import sys

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform training and " +
                                     "decoding with janus")
    parser.add_argument('database', help="sqlite database file")
    parser.add_argument('jobtable', help="table with job configurations")
    parser.add_argument('resulttable', help="table for results")
    parser.add_argument('id', help="row id of configuration to run")
    parser.add_argument(
        '--type',
        choices=['character', 'sentence', 'trainchar', 'words'],
        default='character')
    parser.add_argument('--dir',
                        type=str,
                        help="base directory to run job in (default tmp)")
    parser.add_argument('-k',
                        '--keepfiles',
                        help="keep files after running",
                        action="store_true")
    parser.add_argument('--modeltable', help="table with existing models")
    args = parser.parse_args()

    print()
    print("****** Starting Janus Airwriting train + decode with args:")
    pprint.pprint(args)
    print()

    controlDb = Database.Database()
    controlDb.open(args.database)
    config = airwritingConfig.JanusConfig()
    config.getFromDb(controlDb, args.jobtable, args.id)

    print("Using config:")
    pprint.pprint(config._values)
    print()

    #start time measurement
    starttime = time.time()

    #prepare a directory for the run
    dir = tempfile.mkdtemp(prefix=str(config['orig_id']) + "_airwriting",
                           dir=args.dir)
    print(("Preparing directory: %s" % (dir)))
    if args.type == 'sentence':
        #trainset = config['trainSet']
        #testset = config['testSet']
        config['trainset'] = config['chartrainset']
        config['testset'] = ""
        refkey = "reference"
        hypkey = "hypothesis"
    elif args.type in ['character', 'trainchar']:
        refkey = "text"
        hypkey = "hyp"
    elif args.type in ['words']:
        refkey = "text"
        hypkey = "hypothesis"

    config.writeLocalConfig(dir)

    #run initialization
    os.chdir(dir)
    environ = os.environ
    environ['JANUSHOME'] = "/home/camma/svn/csl-ibis-amma"
    januscmd = "/home/camma/svn/csl-ibis-amma/src/Linux.i686-gcc-ltcl8.4-NX/janus"

    logfile = "stdouterr.log"
    with open(logfile, "w") as logfh:
        if args.type == 'character':
            runscript = "/home/camma/scripts/localrun.init.tcl"
            cmd = [januscmd, runscript]
            print(("Run janus script with: " + " ".join(cmd)))
            retcode = subprocess.call(cmd,
                                      env=environ,
                                      stderr=subprocess.STDOUT,
                                      stdout=logfh)
            print((" ".join(cmd) + " exited with return code " + str(retcode)))
            if retcode != 0:
                print("Janus script had errors, aborting job")
                sys.exit(1)
        elif args.type == 'words':
            identparams = ('hmmstates', 'gmm', 'channels', 'filter',
                           'hmm_repos_states', 'gmm_repos')
            iterations = config['modeliterations']
            params = [
                x + " = " + config._sqlize(config[x]) for x in identparams
            ]
            whereexp = " AND ".join(params) + " AND nriter = " + str(
                iterations)
            sqlcmd = "SELECT distribWeights, codebookWeights FROM %s WHERE %s" % (
                args.modeltable, whereexp)
            dbres = [x for x in controlDb.executeStatement(sqlcmd)]
            print(dbres)
            assert (len(dbres) == 1)
            modeldir = os.path.dirname(dbres[0]['distribWeights'])
            modelFileNames = [
                "codebookSet", "dummycbw", "distribSet", "dummydss",
                "topologies", "topologyTree", "distribTree", "phonesSet",
                "transitionModels"
            ]
            models = list(
                zip(airwritingConfig.JanusConfig.modelFileKeys,
                    [os.path.join(modeldir, f) for f in modelFileNames]))
            #models.append(("codebookWeightsFile", dbres[0]['codebookWeights']))
            #models.append(("distribWeightsFile", dbres[0]['distribWeights']))
            print(models)
            for key, file in models:
                config[key] = file
            config["codebookWeightsFile"] = dbres[0]['codebookWeights']
            dssfile = dbres[0]['distribWeights']
            dssfile = dssfile.replace("Weigths", "Weights")
            config["distribWeightsFile"] = dssfile
            print(config)
            config.writeLocalConfig(dir)
            runscript = "/project/AMR/Handwriting/scripts/runnerTrain.tcl"
            cmd = [januscmd, runscript]
            print(("Run janus script with: " + " ".join(cmd)))
            retcode = subprocess.call(cmd,
                                      env=environ,
                                      stderr=subprocess.STDOUT,
                                      stdout=logfh)
            print((" ".join(cmd) + " exited with return code " + str(retcode)))
            if retcode != 0:
                print("Janus script had errors, aborting job")
                sys.exit(1)
        elif args.type == 'sentence':
            identparams = ('hmmstates', 'gmm', 'channels', 'filter',
                           'hmm_repos_states', 'gmm_repos')
            iterations = config['modeliterations']
            params = [
                x + " = " + config._sqlize(config[x]) for x in identparams
            ]
            whereexp = " AND ".join(params) + " AND nriter = " + str(
                iterations)
            #whereexp = " AND ".join(params) + " AND nriter = 1"
            sqlcmd = "SELECT distribWeights, codebookWeights FROM %s WHERE %s" % (
                args.modeltable, whereexp)
            dbres = [x for x in controlDb.executeStatement(sqlcmd)]
            print(dbres)
            assert (len(dbres) == 1)
            modeldir = os.path.dirname(dbres[0]['distribWeights'])
            modelFileNames = [
                "codebookSet", "dummycbw", "distribSet", "dummydss",
                "topologies", "topologyTree", "distribTree", "phonesSet",
                "transitionModels"
            ]
            models = list(
                zip(airwritingConfig.JanusConfig.modelFileKeys,
                    [os.path.join(modeldir, f) for f in modelFileNames]))
            #models.append(("codebookWeightsFile", dbres[0]['codebookWeights']))
            #models.append(("distribWeightsFile", dbres[0]['distribWeights']))
            print(models)
            for key, file in models:
                config[key] = file
            config["codebookWeightsFile"] = dbres[0]['codebookWeights']
            config["distribWeightsFile"] = dbres[0]['distribWeights']

    if args.type == 'sentence':
        print("Setting up configuration for sentence evaluation")
        print((config._values))
        del config['trainset']
        del config['testset']
        config['feataccess'] = config['feataccessSen']
        config['datadir'] = config['dataDirSen']
        config['dbname'] = config['dbSen']
        config['dict'] = config['dictSen']
        config['vocab'] = config['vocabSen']
        config['tokenSequenceModelFile'] = config['bigram']
        config['LMType'] = "ngram"
        config['iterations'] = config['seniterations']
        config['transcriptkey'] = config['transcriptkeySen']
        #config['trainSet'] = trainset
        #config['testSet'] = testset
        config.writeLocalConfig(dir)
        runscript = "/project/AMR/Handwriting/scripts/runner.tcl"
        cmd = [januscmd, runscript]
        print(("Run janus script with: " + " ".join(cmd)))
        with open("sentence.log", "w") as logfh:
            retcode = subprocess.call(cmd,
                                      env=environ,
                                      stderr=subprocess.STDOUT,
                                      stdout=logfh)
        print((" ".join(cmd) + " exited with return code " + str(retcode)))
        if retcode != 0:
            print("Janus script had errors, aborting job")
            sys.exit(1)

    #stop time measurement
    stoptime = time.time()
    duration = stoptime - starttime
    print(("Duration: " + str(duration)))
    config['cputime'] = duration

    config['hostname'] = socket.gethostname()

    # treat number of iterations as an implicit given config range
    for iter in range(config['iterations'] + 1):
        #include model files in database
        config['distribWeights'] = os.path.abspath('distribWeights.' +
                                                   str(iter))
        config['codebookWeights'] = os.path.abspath('codebookWeights.' +
                                                    str(iter))
        config['nriter'] = iter
        results = None
        if not args.type in ['character', 'words']:
            resfile = "result.iter" + str(iter) + ".csv"
            print(("reading result file: " + resfile))
            with open(resfile, "r") as resultfh:
                results = airwritingUtil.readResultFile(resultfh)
        postrun.postrun(results, config, args.database, args.resulttable,
                        config['nrfolds'], refkey, hypkey)

    print("****job finished, deleting from database")
    controlDb.executeStatement("DELETE FROM " + args.jobtable + " WHERE " +
                               "id = " + str(config["orig_id"]))
    controlDb.close()
    if not args.keepfiles:
        print("****deleting temporary directory")
        shutil.rmtree(dir)
    print("exit with return code 0")
    sys.exit(0)

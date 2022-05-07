import sys
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
import datetime
import json

from .runjanus import *
from .runbiokit import *


def log(level, text):
    print("Python log: " + str(datetime.datetime.now()) + " - " + level +
          ": " + text)


def add_results_to_db(session, ter, iter, config, reslist=None):
    """
    Add the TER for the given configuration and iteration to the database
    """
    result = db.Result(ter=ter, iteration=iter, configuration=config)
    session.add(result)
    if reslist:
        rlist = db.ResultList(result=result, resjson=json.dumps(reslist))
        session.add(rlist)
    log("Info", "Adding Result to Database: %s" % result)
    #airdb.insert_unique(result)
    session.commit()
    return result


def add_blame_to_db(session, result, blamelog, confusionmap):
    blame = db.ErrorBlame(result=result,
                          blamelog=json.dumps(blamelog),
                          confusionmap=json.dumps(confusionmap))
    session.add(blame)
    session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform training and " +
                                     "decoding")
    parser.add_argument('database', help="sqlite database file")
    parser.add_argument('id', help="row id of job to run")
    parser.add_argument('--dir',
                        type=str,
                        help="base directory to run job in (default tmp)")
    parser.add_argument('-k',
                        '--keepfiles',
                        help="keep files after running",
                        action="store_true")
    parser.add_argument('-b',
                        '--blame',
                        help="perform error blaming on biokit decoding",
                        action="store_true")
    parser.add_argument('--janushome',
                        default="/home/camma/svn/ibis-v5_1_1-bugFixed" +
                        "/ibis-v5_1_1-bugFixed")
    parser.add_argument(
        '--januscmd',
        default="/home/camma/svn/ibis-v5_1_1-bugFixed" +
        "/ibis-v5_1_1-bugFixed/src/Linux.x86_64-gcc-ltcl8.4-NX/janus")
    #parser.add_argument('--biokitcmd',
    #                    default = "/home/camma/workspace/decoder/release")
    args = parser.parse_args()

    # some constants dependent on janus tcl scripts in use
    refkey = "reference"
    hypokey = "hypothesis"

    print()
    print("****** Starting Airwriting train + decode with args:")
    pprint.pprint(args)
    print()

    janus_home = args.janushome
    janus_cmd = args.januscmd

    airdb = db.AirDb(args.database)
    job = airdb.session.query(db.Job).filter(db.Job.id == args.id).one()
    config = job.configuration

    log("Info", "Using config:")
    pprint.pprint(config.__dict__)
    print()

    log("Info", "Start time measurement")
    starttime = time.time()

    #prepare a directory for the run
    dir = tempfile.mkdtemp(prefix=str(job.id) + "_airwriting", dir=args.dir)
    dir = os.path.abspath(dir)
    print(("Preparing directory for Janus: %s" % (dir)))
    init_janus_rundir(airdb, dir, config)

    existingModels = {}
    log("Info", "Initialize models")
    if not config.basemodel:
        log("Info",
            "No initial model given, checking for existing initial models")
        try:
            modelparams = airdb.find_equal_training_modelsparameters(config, 0)
        except db.MultipleResultsFound as e:
            print((e.msg))
            sys.exit()
        if not modelparams:
            log("Info", "No models available, perform flatstart")
            existingModels[0] = None
            flatstartlog = os.path.join(dir, "flatstart.log")
            with open(flatstartlog, "w") as logfh:
                runscript = "/project/AMR/Handwriting/scripts/flatstart.tcl"
                run_janus_script(dir, runscript, logfh, janus_home, janus_cmd)
        else:
            # models available
            log("Info", "Found models: %s" % (modelparams, ))
            existingModels[0] = modelparams
            write_initial_model_files_normalized(dir, modelparams)
    else:
        log("Info", "Use given base models for initialization")
        existingModels[0] = config.basemodel
        write_initial_model_files_normalized(dir, config.basemodel)

    log("Info", "Checking for existing models for the training iterations")
    modelsnotfound = False
    for iter in range(1, config.iterations + 1):
        modelparams = airdb.find_equal_training_modelsparameters(config, iter)
        if modelparams:
            if modelsnotfound:
                log(
                    "Info",
                    "Found existing models for iteration " + str(iter) +
                    "but previous iterations missing. This should not happen!")
                sys.exit()
            log("Info", "Found existing models for iteration %s" % iter)
            log("Info", "ModelsParameters: %s" % modelparams)

            write_model_files_normalized(dir, modelparams)
        else:
            log("Info", "No existing models for iteration %s found" % iter)
            modelsnotfound = True
        existingModels[iter] = modelparams

    trainlog = os.path.join(dir, "train.log")
    with open(trainlog, "w") as logfh:
        log("Info",
            "Training with Janus for %s iterations" % (config.iterations, ))
        # use existing models, the runnerTrain script ignores existing models
        runscript = "/project/AMR/Handwriting/scripts/runnerTrain.tcl"
        run_janus_script(dir, runscript, logfh, janus_home, janus_cmd)

    # create new Modelparameter instances for each iteration if necessary
    log("Info", "Save all new model parameters in database")
    for iter, modelparams in list(existingModels.items()):
        if not modelparams:
            log("Info", "Adding models for iteration %s" % iter)
            modelparam = db.ModelParameters()
            modelparam.read_from_files(
                "codebookSet", "codebookWeights.%s" % iter, "distribSet",
                "distribWeights.%s" % iter, "distribTree", "topologies",
                "topologyTree", "transitionModels", "phonesSet")
            modelparam.iteration = iter
            modelparam.configuration = config
            airdb.session.add(modelparam)
            airdb.session.commit()
        else:
            log(
                "Info", "Models %s for iteration %s already existed." %
                (modelparams, iter))

    #decoding will only be performed if a testset is given
    if config.testset:
        if config.biokitconfig and not config.ibisconfig:
            log("Info", "Perform decoding with BioKIT")
            for iter in range(config.iterations + 1):
                airrec = AirwritingRecognizer(airdb.session)
                if iter == 0 and config.basemodel:
                    modelparam = config.basemodel
                else:
                    modelparam = airdb.find_equal_training_modelsparameters(
                        config, iter)
                log("Info",
                    "Use models for iteration=%s: %s" % (iter, modelparam))
                airrec.setup(config, modelparam, dir)
                resultslist = airrec.decode_set(config.testset, args.blame)
                log("Info", str(resultslist))
                ter = align.totalTokenErrorRate(resultslist)
                log("Info", "Token Error Rate: " + str(ter))
                result = add_results_to_db(airdb.session, ter, iter, config,
                                           resultslist)
                if args.blame:
                    blamelog, confusionmap = airrec.getBlameResults()
                    add_blame_to_db(airdb.session, result, blamelog,
                                    confusionmap)
        elif not config.biokitconfig and config.ibisconfig:
            log("Info", "Perform decoding with Ibis")
            ibislog = os.path.join(dir, "ibis.log")
            with open(ibislog, "w") as logfh:
                # use existing models
                runscript = "/project/AMR/Handwriting/scripts/decode.tcl"
                run_janus_script(dir, runscript, logfh, janus_home, janus_cmd)
            for iter in range(config.iterations + 1):
                resfile = "result.iter" + str(iter) + ".csv"
                log("Info", "reading result file: " + resfile)
                with open(resfile, "r") as resultfh:
                    resultslist = airwritingUtil.readResultFile(resultfh)
                ter = align.totalTokenErrorRate(resultslist, refkey, hypokey)
                log("Info", "Token Error Rate: " + str(ter))
                add_results_to_db(airdb.session, ter, iter, config,
                                  resultslist)
        else:
            log("Info", "ERROR: No or multiple decoding configurations given")
            sys.exit()

    #stop time measurement
    log("Info", "Stopping time measurement")
    stoptime = time.time()
    duration = stoptime - starttime
    print(("Duration: " + str(duration)))
    job.cputime = duration
    job.host = socket.gethostname()
    job.status = "finished"
    print(("Persistent Objects: %s" % str(airdb.session.dirty)))
    airdb.session.commit()
    airdb.close()

    print("****job finished")
    if not args.keepfiles:
        print("****deleting temporary directory")
        shutil.rmtree(dir)
    print("exit with return code 0")
    sys.exit(0)

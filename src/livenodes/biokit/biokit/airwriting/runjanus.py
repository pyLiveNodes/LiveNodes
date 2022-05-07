import sys

sys.path.append('/home/camma/workspace/decoder/python/python-lib')
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


def write_janus_config_file(filename, config):
    s = ''
    s += 'set conf {\n'
    s += 'dbdir "%s"\n' % (os.path.dirname(config.janusdb_name))
    s += 'dbname "%s"\n' % (os.path.basename(config.janusdb_name))
    s += 'datadir "%s"\n' % (config.data_basedir)
    s += 'featdesc "%s"\n' % (config.preprocessing.janus_desc)
    s += 'feataccess "%s"\n' % (config.preprocessing.janus_access)
    s += config.preprocessing.janusConfigStr()
    s += 'vocab "%s"\n' % (config.vocabulary.file)

    ###BAD HACK: Check for biokit specific dictionary
    ### .dec file indicates biokit specific, delete the ending and expect file
    ### file to exist.
    print()
    if os.path.splitext(config.dictionary.file)[1] == '.dec':
        dictfile = os.path.splitext(config.dictionary.file)[0]
    else:
        dictfile = config.dictionary.file
    ###END BAD HACK

    s += 'dict "%s"\n' % (dictfile)
    if config.contextmodel.type.name == "ngram":
        s += 'ngram "%s"\n' % (config.contextmodel.file)
    elif config.contextmodel.type.name == "grammar":
        s += 'grammar "%s"\n' % (config.contextmodel.file)
    else:
        print(("Error: unknown context model type %s" %
               (config.contextmodel.type.name)))
    s += 'phones "%s"\n' % (config.atomset.enumeration)
    s += 'hmmstates %s\n' % (config.topology.hmmstates)
    s += 'hmm_repos_states %s\n' % (config.topology.hmm_repos_states)
    s += 'gmm %s\n' % (config.topology.gmm)
    s += 'gmm_repos %s\n' % (config.topology.gmm_repos)
    s += 'transcriptkey "%s"\n' % (config.transcriptkey)
    s += 'trainset trainSet\n'
    s += 'testset testSet\n'
    s += 'devset ""\n'
    s += 'iterations %s\n' % (config.iterations)
    s += 'dirname "%s"\n' % (os.path.dirname(filename))
    # only write ibisconfig if available to allow for training only wiht janus
    if config.ibisconfig:
        s += 'wordPen %s\n' % (config.ibisconfig.wordPen)
        s += 'lz %s\n' % (config.ibisconfig.lz)
        s += 'wordBeam %s\n' % (config.ibisconfig.wordBeam)
        s += 'stateBeam %s\n' % (config.ibisconfig.stateBeam)
        s += 'morphBeam %s\n' % (config.ibisconfig.morphBeam)
    s += '}'
    with open(filename, 'w') as f:
        f.write(s)


def write_initial_model_files_normalized(dirname, modelparam):
    """
    Write the data of a modelparam object with standard filenames to directory.
    
    The codebook and distrib weights are written to the target files
    codebookWeights and codebookWeights.0 (distribWeights and distribWeights.0). 
    """
    db.write_blob(modelparam.gaussian_desc,
                  os.path.join(dirname, "codebookSet"))
    db.write_blob(modelparam.gaussian_data,
                  os.path.join(dirname, "codebookWeights"))
    db.write_blob(modelparam.gaussian_data,
                  os.path.join(dirname, "codebookWeights.0"))
    db.write_blob(modelparam.mixture_desc, os.path.join(dirname, "distribSet"))
    db.write_blob(modelparam.mixture_data,
                  os.path.join(dirname, "distribWeights"))
    db.write_blob(modelparam.mixture_data,
                  os.path.join(dirname, "distribWeights.0"))
    db.write_blob(modelparam.distrib_tree,
                  os.path.join(dirname, "distribTree"))
    db.write_blob(modelparam.topologies, os.path.join(dirname, "topologies"))
    db.write_blob(modelparam.topology_tree,
                  os.path.join(dirname, "topologyTree"))
    db.write_blob(modelparam.transitions,
                  os.path.join(dirname, "transitionModels"))
    db.write_blob(modelparam.phones, os.path.join(dirname, "phonesSet"))
    open(os.path.join(dirname, "tags"), "w").close()


def write_model_files_normalized(dirname, modelparam):
    gaussian_path = os.path.join(dirname,
                                 "codebookWeights.%s" % modelparam.iteration)
    db.write_blob(modelparam.gaussian_data, gaussian_path)
    mixture_path = os.path.join(dirname,
                                "distribWeights.%s" % modelparam.iteration)
    db.write_blob(modelparam.mixture_data, mixture_path)


def copy_model_files_normalized(dirname, modelparam):
    """
    Copy the files of a modelparam object with standard filenames to directory.
    
    The codebook and distrib weights are copied to the target files
    codebookWeights and codebookWeights.0 (distribWeights and distribWeights.0). 
    """
    shutil.copy(modelparam.gaussian_desc, os.path.join(dirname, "codebookSet"))
    shutil.copy(modelparam.gaussian_data,
                os.path.join(dirname, "codebookWeights"))
    shutil.copy(modelparam.gaussian_data,
                os.path.join(dirname, "codebookWeights.0"))
    shutil.copy(modelparam.mixture_desc, os.path.join(dirname, "distribSet"))
    shutil.copy(modelparam.mixture_data, os.path.join(dirname,
                                                      "distribWeights"))
    shutil.copy(modelparam.mixture_data,
                os.path.join(dirname, "distribWeights.0"))
    shutil.copy(modelparam.distrib_tree, os.path.join(dirname, "distribTree"))
    shutil.copy(modelparam.topologies, os.path.join(dirname, "topologies"))
    shutil.copy(modelparam.topology_tree, os.path.join(dirname,
                                                       "topologyTree"))
    shutil.copy(modelparam.transitions,
                os.path.join(dirname, "transitionModels"))
    shutil.copy(modelparam.phones, os.path.join(dirname, "phonesSet"))
    open(os.path.join(dirname, "tags"), "w").close()


def copy_description_files(dirname, modelparam, createTags=True):
    """
    Copy the files referenced by a modelparam object to a given directory.
    
    The filenames are preserved during copy, existing files are overwritten.
    If you use janus scripts expecting certain filenames, try 
    copy_model_files_normalized. An empty "tags" file is created in the given
    directory by default. 
    
    Keyword arguments:
    dirname - target directory, must already exist
    modelparam - instance of db.ModelParameters referencing the files
    createTags - indicate if an empty tags file should be created (default True)
    """
    shutil.copy(modelparam.gaussian_desc, dirname)
    shutil.copy(modelparam.gaussian_data, dirname)
    shutil.copy(modelparam.mixture_desc, dirname)
    shutil.copy(modelparam.mixture_data, dirname)
    shutil.copy(modelparam.distrib_tree, dirname)
    shutil.copy(modelparam.topologies, dirname)
    shutil.copy(modelparam.topology_tree, dirname)
    shutil.copy(modelparam.transitions, dirname)
    shutil.copy(modelparam.phones, dirname)
    if createTags:
        open(os.path.join(dirname, "tags"), "w").close()


def copy_model_parameter_files(dirname, modelparam):
    """
    Copy mixture weights and gaussians to target directory. The filenames are
    kept.
    
    Keyword arguments:
    modelparam - Instance of ModelParameters storing the paths to model files.
    """
    shutil.copy(modelparam.gaussian_data, dirname)
    shutil.copy(modelparam.mixture_data, dirname)


def init_janus_rundir(airdb, dirname, config):
    write_janus_config_file(os.path.join(dirname, "rec.conf.tcl"), config)
    if config.trainset:
        airdb.write_janus_dataset(config.trainset,
                                  os.path.join(dirname, "trainSet"))
    if config.testset:
        airdb.write_janus_dataset(config.testset,
                                  os.path.join(dirname, "testSet"))

    #if config.basemodel:
    #    #base models are present
    #    write_initial_model_files_normalized(dirname, config.basemodel)


def run_janus_script(dir, script, logfile_handle, janus_home, januscmd):
    """
    Run a Janus Tcl script. 
    
    Keyword arguments:
    dir - directory to run the script in
    script - Janus Tcl script to run
    logfile_handle - an open file handle for log messages
    """
    os.chdir(dir)
    environ = os.environ
    #environ['LD_LIBRARY_PATH'] = "/home/camma/janusbin"
    environ['JANUSHOME'] = janus_home
    januscmd = januscmd

    cmd = [januscmd, script]
    print(("Run janus script with: " + " ".join(cmd)))
    retcode = subprocess.call(cmd,
                              env=environ,
                              stderr=subprocess.STDOUT,
                              stdout=logfile_handle)
    print((" ".join(cmd) + " exited with return code " + str(retcode)))
    if retcode != 0:
        print("Janus script had errors, aborting job")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform training and " +
                                     "decoding with janus")
    parser.add_argument('database', help="sqlite database file")
    parser.add_argument('id', help="row id of job to run")
    #parser.add_argument('--dir', type = str,
    #                    help = "base directory to run job in (default tmp)")
    parser.add_argument('-k',
                        '--keepfiles',
                        help="keep files after running",
                        action="store_true")
    parser.add_argument('--janushome', default="/home/camma/svn/csl-ibis-amma")
    parser.add_argument(
        '--januscmd',
        default=
        "/home/camma/svn/csl-ibis-amma/src/Linux.i686-gcc-ltcl8.4-NX/janus")
    args = parser.parse_args()

    # some constants dependent on tcl scripts in use
    refkey = "reference"
    hypokey = "hypothesis"

    print()
    print("****** Starting Janus Airwriting train + decode with args:")
    pprint.pprint(args)
    print()

    janus_home = args.janushome
    janus_cmd = args.januscmd

    airdb = db.AirDb(args.database)
    job = airdb.session.query(db.Job).filter(db.Job.id == args.id).one()
    config = job.configuration

    print("Using config:")
    pprint.pprint(config.__dict__)
    print()

    #start time measurement
    starttime = time.time()

    #prepare a directory for the run
    dir = tempfile.mkdtemp(prefix=str(job.id) + "_airwriting", dir=".")
    dir = os.path.abspath(dir)
    print(("Preparing directory for Janus: %s" % (dir)))
    init_janus_rundir(airdb, dir, config)

    #run initialization
    if not config.basemodel:
        flatstartlog = os.path.join(dir, "flatstart.log")
        with open(flatstartlog, "w") as logfh:
            # flatstart
            runscript = "/project/AMR/Handwriting/scripts/flatstart.tcl"
            run_janus_script(dir, runscript, logfh, janus_home, janus_cmd)
    trainlog = os.path.join(dir, "train.log")
    with open(trainlog, "w") as logfh:
        # use existing models
        runscript = "/project/AMR/Handwriting/scripts/runner.tcl"
        run_janus_script(dir, runscript, logfh, janus_home, janus_cmd)

    #stop time measurement
    stoptime = time.time()
    duration = stoptime - starttime
    print(("Duration: " + str(duration)))
    job.cputime = duration
    job.host = socket.gethostname()

    # create new Modelparameter instances for each iteration
    for iter in range(config.iterations + 1):
        modelparam = db.ModelParameters()
        modelparam.distrib_tree = os.path.abspath('distribTree')
        modelparam.topologies = os.path.abspath('topologies')
        modelparam.topology_tree = os.path.abspath('topologyTree')
        modelparam.transitions = os.path.abspath('transitionModels')
        modelparam.phones = os.path.abspath('phoneSet')
        modelparam.gaussian_desc = os.path.abspath('codebookSet')
        modelparam.gaussian_data = os.path.abspath('codebookWeights.' +
                                                   str(iter))
        modelparam.mixture_desc = os.path.abspath('distribSet')
        modelparam.mixture_data = os.path.abspath('distribWeights.' +
                                                  str(iter))
        modelparam.iteration = iter
        modelparam.configuration = config
        airdb.session.add(modelparam)
        if config.testset:
            resfile = "result.iter" + str(iter) + ".csv"
            print(("reading result file: " + resfile))
            with open(resfile, "r") as resultfh:
                resultslist = airwritingUtil.readResultFile(resultfh)
            ter = align.totalTokenErrorRate(resultslist, refkey, hypokey)
            result = db.Result()
            result.ter = ter
            result.iteration = iter
            result.configuration = config
            airdb.session.add(result)

    job.status = "finished"
    airdb.session.commit()

    print("****job finished")
    if not args.keepfiles:
        print("****deleting temporary directory")
        shutil.rmtree(dir)
    print("exit with return code 0")
    sys.exit(0)


import sys
import argparse
import pprint
import tempfile
import os
import shutil
from . import db
from . import airwritingUtil
import align
import time
import datetime
import recognizer
from . import util
import numpy
import json
import visualization as vis


from .runbiokit import *


def log(level, text):
    print("Python log: %s - %s: %s" % (str(datetime.datetime.now()),
                                       level, text))

        
def write_biokit_initial_model_files(dir, modelparam, dictionary):
    """
    Write the data of a modelparam object with standard filenames to directory.
    
    The codebook and distrib weights are written to the target files
    codebookWeights and codebookWeights.0 (distribWeights and distribWeights.0). 
    """
    log("Info", "Writing model files to directory: %s" % dir) 
    db.write_blob(modelparam.gaussian_desc,
                os.path.join(dir, "gaussianDesc"))
    db.write_blob(modelparam.gaussian_data,
                os.path.join(dir, "gaussianData"))
    db.write_blob(modelparam.mixture_desc,
                os.path.join(dir, "mixtureDesc"))
    db.write_blob(modelparam.mixture_data,
                os.path.join(dir, "mixtureData"))
    db.write_blob(modelparam.distrib_tree,
                os.path.join(dir, "mixtureTree"))
    db.write_blob(modelparam.topologies,
                os.path.join(dir, "topologies"))
    db.write_blob(modelparam.topology_tree,
                os.path.join(dir, "topologyTree"))
    db.write_blob(modelparam.phones,
                os.path.join(dir, "atomMap"))
    shutil.copy(dictionary.file,
                os.path.join(dir, "dictionary"))
    
def delete_reco_files(dir):
    """Delete files created by Recognizer.saveToFiles in given directory."""
    log("Info", "Deleting model files in directory: %s" % dir)
    filenames = ["gaussianDesc", "gaussianData", "mixtureDesc", "mixtureData",
                 "mixtureTree", "topologyTree", "topologies", "atomMap",
                 "dictionary"]
    for f in filenames:
        os.remove(os.path.join(dir, f))
        
def add_results_to_db(session, ter, iter, config, hypolist=None):
    """
    Add the TER for the given configuration and iteration to the database
    """
    result = db.Result(ter=ter, iteration=iter, configuration=config)
    log("Info", "Adding result to database: %s" % result)
    session.add(result)
    session.commit()
    if hypolist:
        reslist = db.ResultList(result=result, resjson=json.dumps(hypolist))
        log("Info", "Adding result list to database: %s" % reslist)
        session.add(reslist)
        session.commit()
    return result
        
def add_blame_to_db(session, result, blamelog, confusionmap):
    blame = db.ErrorBlame(result=result,
                          blamelog=json.dumps(blamelog),
                          confusionmap=json.dumps(confusionmap))
    session.add(blame)
    session.commit()
    
    
def initializeRecognizer(modelparam, config, dir=None):
    """
    Return an initialized Recognizer instance with the given configuration.
    """
    write_biokit_initial_model_files(dir,
                                     modelparam,
                                     config.dictionary)
    # As we need to use fillers, we cannot use Recognizer.createFromFile
    topologyInfo = BioKIT.TopologyInfo()
    gaussianContainerSet = BioKIT.GaussianContainerSet()
    gaussMixturesSet = BioKIT.GaussMixturesSet(gaussianContainerSet)
    gmmScorer = BioKIT.GmmFeatureVectorScorer(gaussMixturesSet)
    mixtureTree = BioKIT.MixtureTree(gmmScorer)
    atomManager = BioKIT.AtomManager()
    gaussianContainerSet.readDescFile(os.sep.join([dir, 'gaussianDesc']))
    gaussianContainerSet.loadDataFile(os.sep.join([dir, 'gaussianData']))
    gaussMixturesSet.readDescFile(os.sep.join([dir, 'mixtureDesc']))
    gaussMixturesSet.loadDataFile(os.sep.join([dir, 'mixtureData']))
    atomManager.readAtomManager(os.sep.join([dir, 'atomMap']))
    mixtureTree.readTree(os.sep.join([dir, 'mixtureTree']))
    topologyInfo.readTopologyTree(os.sep.join([dir, 'topologyTree']))
    topologyInfo.readTopologies(os.sep.join([dir, 'topologies']))
    dictionary = BioKIT.Dictionary(atomManager)
    dictionary.registerAttributeHandler("FILLER", BioKIT.NumericValueHandler())
    dictionary.readDictionary(os.sep.join([dir, 'dictionary']))
    vocabulary = BioKIT.SearchVocabulary(dictionary)  
    if config.contextmodel.type.name == "grammar":
        #TODO: use given grammar instead of AtomGrammar
        reco = recognizer.Recognizer.createNewFromFile(dir)
    elif config.contextmodel.type.name == "ngram":
        ngram = BioKIT.NGram(dictionary)
        ngram.readArpaFile(config.contextmodel.file)
        fillerWrapper = BioKIT.FillerWrapper(ngram, dictionary, "FILLER")
        cacheTsm = BioKIT.CacheTokenSequenceModel(fillerWrapper, dictionary)
        tsm = cacheTsm
        reco = recognizer.Recognizer.createNewFromFile(dir, tsm, True)
    return reco

def getSilFeatures(fs):
    """
    Return first and last feature vector of feature sequence as 
    new feature sequence.

    Taken as samples for silence model.
    """
    v1 = fs.getMatrix()[0,:]
    v2 = fs.getMatrix()[-1,:]
    sildata = numpy.vstack((v1,v2))
    silfs = BioKIT.FeatureSequence()
    silfs.setMatrix(sildata)
    return silfs

def set_beams(reco, config):
    #incredibly high beams
    reco.setTrainingBeams(1000,
                          100,
                          1000,
                          100000,
                          1000,
                          100)
    if config.biokitconfig:
        reco.setBeams(config.biokitconfig.hypo_beam,
                      config.biokitconfig.hypo_topn,
                      config.biokitconfig.active_node_beam,
                      config.biokitconfig.active_node_topn,
                      config.biokitconfig.final_node_beam,
                      config.biokitconfig.final_node_topn)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform training and " +
                                     "decoding with BioKIT")
    parser.add_argument('database', help = "sqlite database file")
    parser.add_argument('id', help = "row id of job to run")
    parser.add_argument('--dir', type = str,
                        help = "base directory to run job in (default tmp)")
    parser.add_argument('-k', '--keepfiles', help = "keep files after running",
                        action="store_true")
    parser.add_argument('-b', '--blame', help = "perform error blaming", 
                        action="store_true")
    args = parser.parse_args()
    
    # some constants dependent on janus tcl scripts in use
    refkey = "reference"
    hypokey = "hypothesis"

    print("")
    print("****** Starting BioKit train + decode with args:")
    pprint.pprint(args)
    print("")
    
    airdb = db.AirDb(args.database)
    job = airdb.session.query(db.Job).filter(db.Job.id==args.id).one()
    config = job.configuration
        
    log("Info", "Using config:")
    pprint.pprint(config.__dict__)
    print("")
    
    log("Info", "Start time measurement")
    starttime = time.time()
    
    #prepare a directory for the run
    dir = tempfile.mkdtemp(prefix = str(job.id) + "_airwriting", dir = args.dir)
    dir = os.path.abspath(dir)
    
    #dynamically import prepro module
    prepro_module = config.preprocessing.biokit_desc
    pp = __import__(prepro_module)
    prepro = pp.PrePro()
    
    #precompute features
    fsstorage = util.FeatureSequenceStorage(config, prepro)
    
    legacycompat = False
    
    existingModels = None
    log("Info", "Initialize models")
    if not config.basemodel:
        log("Info", "No basemodel given, perform flatstart")
        modelsDoExist = False
        #initialize recognizer
        statelist = [str(x) for x in range(config.topology.hmmstates)]
        atomlist_utf = config.atomset.enumeration.split()
        atomlist = [x.encode('ascii') for x in atomlist_utf]
        ##### Another hack to include the SIL model
        atomtopo = {atom: statelist for atom in atomlist if atom is not "SIL"}
        if "SIL" in atomlist:
            legacycompat = True
            atomtopo["SIL"] = ["0"]
        print(atomtopo)
        ##### UHHHHH THIS IS WRONG!!! WORKS ONLY IF WE INIT ON ATOM=TOKEN
        #dictionary = {atom: [atom] for atom in atomlist}
        #with open(config.dictionary.file) as df:
            
        print(dictionary)
        
        reco = recognizer.Recognizer.createCompletelyNew(
                            atomtopo,
                            dictionary,
                            config.topology.gmm,
                            prepro.getFeatureDim())
        set_beams(reco, config)
        for recording in config.trainset.recordings:
            fs = fsstorage.get(recording.id)
            if legacycompat:
                silfs = getSilFeatures(fs)
                reco.storeAtomForInit(silfs, "SIL")
            reco.storeAtomForInit(fs, recording.reference.encode('ascii'))
        reco.initializeStoredModels()
        reco.saveToFiles(dir)
        modelparam = db.ModelParameters()
        modelparam.read_from_biokit_files(os.path.join(dir,"gaussianDesc"),
                                          os.path.join(dir,"gaussianData"), 
                                          os.path.join(dir,"mixtureDesc"),
                                          os.path.join(dir,"mixtureData"), 
                                          os.path.join(dir,"mixtureTree"),
                                          os.path.join(dir,"topologies"),
                                          os.path.join(dir,"topologyTree"),
                                          os.path.join(dir,"atomMap"))
        modelparam.iteration = 0
        modelparam.configuration = config
        airdb.session.add(modelparam)
        airdb.session.commit()
        existingModels = modelparam
    else:
        existingModels = config.basemodel
    write_biokit_initial_model_files(dir, existingModels, config.dictionary)
    reco = recognizer.Recognizer.createNewFromFile(dir)
    set_beams(reco, config)    
        
    log("Info", "Checking for existing models for the training iterations")
    modelsnotfound = False
    for iter in range(1,config.iterations+1):
        no_path_recs = []
        modelparams = airdb.find_equal_training_modelsparameters(
                                                        config, 
                                                        iter)
        if modelparams:
            if modelsnotfound:
                log("Info", "Found existing models for iteration " + str(iter) +
                    "but previous iterations missing. This should not happen!")
                sys.exit()
            log("Info", "Found existing models for iteration %s" % iter)
            log("Info", "ModelsParameters: %s" % modelparams)
            
        else:
            log("Info", "No existing models for iteration %s found" % iter)
            log("Info", "Start training iteration %s " % iter)
            for recording in config.trainset.recordings:
                print(".", end="")
                fs = fsstorage.get(recording.id)
                if legacycompat:
                    # do it the legacy way and assign first and last feature
                    # vector additionally to silence
                    silfs = getSilFeatures(fs)
                    reco.storeTokenForTrain(silfs, "SIL")
                try:
                    tokensequence = recording.reference.encode('ascii').split()
                    reco.storeTokenSequenceForTrain(fs, tokensequence)
                except recognizer.NoViterbiPath as e:
                    print("No path was found for %s, storing id" % recording)
                    no_path_recs.append((recording.id, recording.reference, 
                                         recording.filename))
            print("No paths were found for: %s" % no_path_recs)
            with open(os.path.join(dir,"nopathids.%s.json" % iter), "w") as f:
                f.write(json.dumps(no_path_recs))
            reco.finishTrainIteration()
            delete_reco_files(dir)
            reco.saveToFiles(dir)
            modelparam = db.ModelParameters()
            modelparam.read_from_biokit_files(os.path.join(dir,"gaussianDesc"),
                                               os.path.join(dir,"gaussianData"), 
                                               os.path.join(dir,"mixtureDesc"),
                                               os.path.join(dir,"mixtureData"), 
                                               os.path.join(dir,"mixtureTree"),
                                               os.path.join(dir,"topologies"),
                                               os.path.join(dir,"topologyTree"),
                                               os.path.join(dir,"atomMap"))
            modelparam.iteration = iter
            modelparam.configuration = config
            airdb.session.add(modelparam)
            airdb.session.commit()
            modelsnotfound = True
    
    #decoding will only be performed if a testset is given
    if config.testset:
        if config.biokitconfig and not config.ibisconfig:
            log("Info", "Perform decoding with BioKIT")
            for iter in range(config.iterations+1):
                airrec = AirwritingRecognizer(airdb.session)
                if iter == 0 and config.basemodel:
                    modelparam = config.basemodel
                else:
                    modelparam = airdb.find_equal_training_modelsparameters(
                                    config, iter)
                log("Info", "Use models for iteration=%s: %s" % (iter,modelparam))
                reco = initializeRecognizer(modelparam, config, dir)
                for recording in config.testset.recordings:
                    filename = os.path.join(config.data_basedir,
                                        recording.experiment.base_dir,
                                        recording.filename)
                    log("Info", "process: %s" % (filename,))
                    mcfs = prepro.process(filename)
                    #util.writeMcfsToAdc(mcfs, filename+".stdprepro")
                    reco.decode(mcfs[0], recording.reference.encode('ascii'))
                    if args.blame:
                        log("Info", "Perform Error Blaming")
                        reco.storeSequenceForBlame(
                                   mcfs[0],
                                   recording.reference.encode('ascii').split(),
                                   recording.id,
                                   0.7)
                log("Info", "**** Decoding complete *****")
                ter = reco.getDecodingTER()
                reco.clearDecodingList()
                log("Info", str(reco.getDecodingResult()))
                log("Info", "Token Error Rate: " + str(ter))
                result = add_results_to_db(airdb.session, ter, iter, config)
                if args.blame:
                    blamelog, confusionmap = reco.getBlameResults()
                    add_blame_to_db(airdb.session, result, blamelog, confusionmap)
                
                    
        else:
            log("Info", "ERROR: No or multiple decoding configurations given")
            sys.exit()        
              
    #stop time measurement
    log("Info", "Stopping time measurement")
    stoptime = time.time()
    duration = stoptime - starttime
    print("Duration: " + str(duration))
    job.cputime = duration
    job.host = socket.gethostname()
    job.status = "finished"
    airdb.session.commit()
            
    print("****job finished")
    if not args.keepfiles:
        print("****deleting temporary directory")
        shutil.rmtree(dir)
    print("exit with return code 0")
    sys.exit(0)

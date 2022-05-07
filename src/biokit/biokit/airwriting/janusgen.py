import sys
import os
import string
from . import airwritingConfig
from . import AirwritingDb
import pprint
import argparse
from . import CrossValidation

def addExperiment(foldgen, config, db, jobtable, resulttable,
                  allowDuplicate = False, exptype = 'character'):
    #generate experiment Id
    if db.doesTableExist(jobtable) and (db.getNumberOfRecords(jobtable) > 0):
        maxidjob = list(db.executeStatement("SELECT max(expId) FROM " + jobtable))
    else:
        maxidjob = []
    print(("Found maximum job id: " + str(maxidjob))) 
    if (db.doesTableExist(resulttable)):
        maxidresult = list(db.executeStatement("SELECT max(expId) FROM " + resulttable))
    else:
        maxidresult = []
    print(("Found maximum result id: " + str(maxidresult)))
        
    if len(maxidjob) > 0:
        nextidjob = int(maxidjob[0]['max(expId)']) + 1
    else:
        nextidjob = 0
    if len(maxidresult) > 0:
        nextidresult = int(maxidresult[0]['max(expId)']) + 1
    else:
        nextidresult = 0
    expid = max(nextidjob, nextidresult)
    config['expId'] = expid
    for fold in foldgen:
        #print("fold: ")
        #print(fold)
        config['cvkeyval'] = fold['keyval']
        config['nrfolds'] = fold['nrfolds']
        #bad hack, the config class currently decides what to do based
        #on lower or uppercase S/s in set.
        if exptype in ['character', "words"]:
            config['trainset'] = fold['trainSet']
            config['testset'] = fold['testSet']
            config['devset'] = ""
        elif exptype == 'sentence':
            #del config['trainset']
            #del config['testset']
            config['trainSet'] = sorted([x['id'] for x in fold['trainSet']])
            config['testSet'] = sorted([x['id'] for x in fold['testSet']])
            config['devset'] = ""

        config.generateConfigTable(db, jobtable)
        if not allowDuplicate:
            if config.countInDb(db, jobtable, "expId") == 0:
                if (not db.doesTableExist(resulttable) or
                    (db.doesTableExist(resulttable) and                
                     config.countInDb(db, resulttable, "expId") == 0)):
                    print("configuration not present, inserting")
                    config.insertIntoDb(db, jobtable)
        else:
            config.insertIntoDb(db, jobtable)

def readsetfile(filename):
    """Read database ids from a file
    
    Ids must be given in one line, each seperated by a whitespace"""
    with open(filename, 'r') as fh:
        lines = fh.readlines()
        assert len(lines) == 1
        ids = lines[0].strip().split(" ")
    return ids

def fixedsetgen():
    """Generator for cv folds given as files, hardcoded, not for reuse"""
    setdir = "/project/AMR/Handwriting/data/da/l25e/kfold_rh"
    files = os.listdir(setdir)
    testsets = [s for s in files if s[:4] == 'test']
    testsets.sort()
    trainsets = [s for s in files if s[:4] == 'trai']
    trainsets.sort()
    sets = list(zip(trainsets, testsets))
    sets = [{'trainSet': x, 'testSet': y, 'keyval': x[-3:]} for x,y in sets]
    nrfolds = len(sets)
    for set in sets:
        #trainids = [{'id': id} for id in 
        #            readsetfile(os.path.join(setdir, set['trainSet']))]
        #testids = [{'id': id} for id in
        #           readsetfile(os.path.join(setdir, set['testSet']))]
        trainids = os.path.join(setdir, set['trainSet'])
        testids = os.path.join(setdir, set['testSet'])
        yield {'trainSet': trainids, 'testSet': testids,
               'keyval': set['keyval'], 'nrfolds': nrfolds}
        
def trainonlygen(setfile):
    """Generator for the train only on all data case"""
    yield {'trainSet': setfile, 'testSet': "", 'keyval': "all", 'nrfolds': 1}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate configs for janus"+
                                     " based training and decoding")
    parser.add_argument('type', help = "character or sentence evaluation",
                        choices = ['character', 'sentence', 'words'])
    parser.add_argument('db', help = "Sqlite database file")
    parser.add_argument('jobtable', help = "DB table for job configs")
    parser.add_argument('resulttable', help = "DB table to store results")
    args = parser.parse_args()

    basedir = "/project/amr2/airwriting/journal/janustest"
    hwdir = "/project/AMR/Handwriting"
    datadbfile = "/project/AMR/Handwriting/data/db/all.sqlite"
    #statdbfile = "/project/amr2/airwriting/journal/statdb.sqlite"
    statdbfile = args.db
    dbResults = AirwritingDb.AirwritingDb()
    dbResults.open(statdbfile)
    jobtable = args.jobtable
    resulttable = args.resulttable
    
    config = airwritingConfig.JanusConfig()
    
    config['datadir'] = os.path.join(hwdir, "data")
    config['dictFile'] = os.path.join(hwdir, 'flat', "dict_alph_rp")
    config['LMType'] = "grammar"
    config['tokenSequenceModelFile'] = os.path.join(hwdir, "flat", "grammar_alph_rp.nav")
    config['dbFile'] = datadbfile
    config['recordingsTable'] = "recordings"
    if args.type == "words":
        config['dictFile'] = os.path.join(hwdir, "flat", "dict_top99")
        config['LMType'] = "grammar"
        config['tokenSequenceModelFile'] = os.path.join(hwdir, "flat",
                                                   "grammar_top99.nav")
    #janus specific
    config['dbdir'] = os.path.join(hwdir, "data/db")
    config['dbname'] = "db_all_rp"
    config['featdesc'] = os.path.join(hwdir, "flat", "featDesc.adis.02.tcl")
    config['feataccess'] = os.path.join(hwdir, "flat", "featAccess.adis.01.tcl")
    config['vocab'] = os.path.join(hwdir, "flat", "vocab_alph_rp")
    config['dict'] = config['dictFile']
    config['feature'] = "ADC"
    config['phones'] = " ".join([c for c in string.lowercase]) + " _"
    config['meansub'] = ""
    config['windowsize'] = 10
    config['frameshift'] = 10
    config['wordPen'] = 50
    config['wordBeam'] = 500
    config['stateBeam'] = 500
    config['morphBeam'] = 500
    config['lz'] = 60.0
    config['hmmstates'] = 30
    config['hmm_repos_states'] = 10
    config['gmm'] = 6
    config['gmm_repos'] = 6
    config['iterations'] = 3
    config['modeliterations'] = 1
    config['channels'] = "{2 3 4 5 6 7}"
    config['filter'] = "{}"
    config['transcriptkey'] = "text"
    if args.type == "words":
        config['dbname'] = "db_tmp"
        config['vocab'] = os.path.join(hwdir, "flat", "vocab_top99")
        
    
    if args.type == 'sentence':
        config['feataccessSen'] = os.path.join(hwdir, "flat", "featAccess.sqlite.tcl")
        config['dataDirSen'] = os.path.join(hwdir, "data", "sentence")
        config['dictSen'] = os.path.join(hwdir, "vocab", "dict.en.10k.merg.norepos.sel_v2")
        config['dictChar'] = config['dict']
        config['bigram'] = os.path.join(hwdir, "lm", "English.vocab.en.10k.merg.sel_v2.lm")
        config['vocabSen'] = os.path.join(hwdir, "vocab", "vocab.en.10k.merg.sel_v2")
        config['vocabChar'] = config['vocab']
        config['dbSen'] = "db_sentences"
        config['chartrainset']= "/project/AMR/Handwriting/data/da/l25e/kfold_rh/allset_rh_nrp"
        config['seniterations'] = config['iterations']
        config['chariterations'] = config['iterations']
        config['transcriptkeySen'] = "reference"
        #experiments to include
        experimentStringIds = ['v053', 'v054', 'v055', 'v056', 'v057', 'v058', 'v059',
                               'v060', 'v061']
        cvViewName = '_tmpRecordingsAll'
        whereClause = " OR ".join(["stringId = '" + x + "'" for x in experimentStringIds])
        sqlCreateView = ("CREATE TEMPORARY VIEW IF NOT EXISTS " + cvViewName
                          + " AS SELECT * FROM allRecordings WHERE " 
                          + whereClause)
        
        db = AirwritingDb.AirwritingDb()
        db.open("/project/AMR/Handwriting/data/db/airwritingSentences.sqlite")
        db.executeStatement(db.createViewCorrectRecordings)
        db.executeStatement(db.createViewAllRecordings)
        db.executeStatement(db.createViewAllCorrectRecordings)
        db.executeStatement(sqlCreateView)
        config['recordingsTable'] = "allCorrectRecordings"
        
    
    confgenerator = airwritingConfig.ConfigGenerator(config)
    
    # add ranges here
    #confgenerator.param_ranges['gmm'] = range(1,4)
    #confgenerator.param_ranges['wordBeam'] = range(500, 2001, 500)
    #confgenerator.param_ranges['stateBeam'] = range(500, 2001, 500)
    #confgenerator.param_ranges['morphBeam'] = range(500, 2001, 500)
    #confgenerator.param_ranges['gmm'] = range(15,20)
    #confgenerator.param_ranges['hmmstates'] = range(30,51)
    #confgenerator.param_ranges['gmm'] = range(1,15,1)
    #confgenerator.param_ranges['hmmstates'] = range(10,31,2)
    
    
    
    for conf in confgenerator.getConfigurations():
        conf['gmm_repos'] = conf['gmm']
        conf['hmm_repos_states'] = conf['hmmstates']/3
        if conf['hmm_repos_states'] == 0:
            conf['hmm_repos_states'] = 1
        if args.type == 'character':
            setfile = "/project/AMR/Handwriting/data/da/rp_rh_fold/all_rp"
            foldGenerator = trainonlygen(setfile)
            #foldGenerator = fixedsetgen()
            #dirs = createFoldDirsWithLocalConfig(expid,
            #    os.path.join(baseDir, str(expid)), foldGenerator, config)
            #jobdirs.extend(dirs)
            addExperiment(foldGenerator, conf, dbResults, jobtable, resulttable,
                          exptype = args.type)
        elif args.type == "words":
            setfile = "/project/AMR/Handwriting/data/sets/allwords.set"
            foldGenerator = trainonlygen(setfile)
            addExperiment(foldGenerator, conf, dbResults, jobtable, resulttable,
                          exptype = args.type)
        elif args.type == 'sentence':
            crossValidation = CrossValidation.CrossValidation(db, seed = 1234)
            folds = crossValidation.getPerKeyCrossValidationFolds("name", cvViewName)
            addExperiment(folds, conf, dbResults, jobtable, resulttable,
                          exptype = args.type)
            
            
        
    dbResults.close()

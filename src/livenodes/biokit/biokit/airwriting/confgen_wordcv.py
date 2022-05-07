import sys
from . import db
import string
from . import crossval
from sqlalchemy import and_
import argparse

foldbasename = "words_norp_all"

def fixedsetgen(airdb):
    """
    Generate a standard predefined cross validation character eval set.
    """
    testsets = airdb.session.query(db.Dataset).\
                filter(db.Dataset.name.like("testset_"+foldbasename+"_%")).\
                order_by(db.Dataset.name)
    trainsets = airdb.session.query(db.Dataset).\
                 filter(db.Dataset.name.like("trainset_"+foldbasename+"_%")).\
                 order_by(db.Dataset.name)
    sets = list(zip(trainsets, testsets))
    nrfolds = len(sets)
    for set in sets:
        yield {'trainset': set[0], 'testset': set[1],
               'keyval': set[0].name[-3:], 'nrfolds': nrfolds}
        
def retrieve_datasets(session, basename):
    """
    Retrieves the folds of a cross validation given by the name of the set.
    
    In order to find the datasets, the name must comply with a specific format,
    which is: basename_[test|train]set_fold_<crossvalidation keyval>. 
    """
    testsets = session.query(db.Dataset).\
                filter(db.Dataset.name.like(basename+"_testset_%")).\
                order_by(db.Dataset.name).all()
    trainsets = session.query(db.Dataset).\
                filter(db.Dataset.name.like(basename+"_trainset_%")).\
                order_by(db.Dataset.name).all()
    assert(len(testsets) == len(trainsets))
    sets = list(zip(trainsets, testsets))
    nrfolds = len(sets)
    for set in sets:
        yield {'trainset': set[0], 'testset': set[1],
               'keyval': set[0].name[-3:], 'nrfolds': nrfolds}
        
    
parser = argparse.ArgumentParser(description="Create a configuration for "+
                                 "character cross validation")
parser.add_argument('database', help="sqlite database file to use")
args = parser.parse_args()

airdb = db.AirDb(args.database)


#Configuration to use

pp = db.get_or_create(airdb.session, db.PreProStandard,
    windowsize = 10,
    frameshift = 10,
    filterstring = "",
    channels = "2 3 4 5 6 7",
    meansub = "",
    feature = "ADC",
    janus_desc = "/project/AMR/Handwriting/flat/featDesc.adis.02.tcl",
    janus_access = "/project/AMR/Handwriting/flat/featAccess.adis.01.tcl",
    biokit_desc = "stdprepro")

#pp = db.get_or_create(airdb.session, db.PreProStandard,
#    windowsize = 10,
#    frameshift = 10,
#    filterstring = "",
#    channels = "1 2 3 4 5 6",
#    meansub = "",
#    feature = "ADC",
#    janus_desc = "/project/AMR/Handwriting/flat/featDesc.adcfile.tcl",
#    janus_access = "/project/AMR/Handwriting/flat/featAccess.stdprepro.tcl",
#    biokit_desc = "stdprepro")


cmtype = db.get_or_create(airdb.session, db.ContextModelType,
    name = "grammar")
cmgrammar = db.get_or_create(airdb.session, db.ContextModel,
    name="grammar_top99",
    file="/project/AMR/Handwriting/flat/grammar_top99.nav",
    type=cmtype)

dictionary = db.get_or_create(airdb.session, db.Dictionary,
    name = "dict_top99_norepo",
    file = "/project/AMR/Handwriting/flat/dict_top99_norepo")

vocabulary = db.get_or_create(airdb.session, db.Vocabulary,
    name = "vocab_top99",
    file = "/project/AMR/Handwriting/flat/vocab_top99")



atomset = db.get_or_create(airdb.session, db.AtomSet,
    name = "alphabet_sil",
    enumeration = (" ".join(string.lowercase)) + " SIL")

topology = db.get_or_create(airdb.session, db.TopologyConfig, 
    hmmstates = 20,
    hmm_repos_states = 10,
    gmm = 6,
    gmm_repos = 2)

ibis = db.get_or_create(airdb.session, db.IbisConfig,
    wordPen = 50,
    lz = 0,
    wordBeam = 500,
    stateBeam = 500,
    morphBeam = 500)

biokit = db.get_or_create(airdb.session, db.BiokitConfig,
    token_insertion_penalty = 0,
    languagemodel_weight = 1,
    hypo_topn = 30,
    hypo_beam = 200,
    final_node_topn = 5,
    final_node_beam = 200,
    active_node_topn = 10000,
    active_node_beam = 1000)

#check for existing models
char_trainset = airdb.session.query(db.Dataset).\
                        filter(db.Dataset.name == "l25_rh_norp_all").one()
#check for existing models
print("Looking for basemodel:")
char_iterations = 3
configs = airdb.session.query(db.Configuration).\
                       filter(and_(
                         db.Configuration.data_basedir == "/project/AMR/Handwriting/data",
                         db.Configuration.janusdb_name == '/project/AMR/Handwriting/data/db/db_tmp',
                         db.Configuration.atomset == atomset,
                         db.Configuration.preprocessing == pp,
                         db.Configuration.topology == topology,
                         db.Configuration.transcriptkey == "text",
                         db.Configuration.trainset == char_trainset)).all()
if len(configs) == 0:
    print("No existing basemodel config found, cannot create config")
    sys.exit(0)
elif len(configs) == 1:
    print(("Found existing config: %s" % configs[0].id))
    basemodel = airdb.session.query(db.ModelParameters).\
        filter(db.ModelParameters.configuration == configs[0]).\
        filter(db.ModelParameters.iteration == char_iterations).one()
else:
    print(("Found %s configurations matching the query:" % (len(configs), )))
    print(configs)
    print("Multiple base configs found, this should not happen")
    sys.exit(0)


cvfoldgenerator = retrieve_datasets(airdb.session, foldbasename)
cvconfigs = []
for fold in cvfoldgenerator:
    train_ids = [x.id for x in fold['trainset'].recordings]
    test_ids = [x.id for x in fold['testset'].recordings]
    config = db.get_or_create(airdb.session, db.Configuration,
        data_basedir = "/project/AMR/Handwriting/data",
        janusdb_name = "/project/AMR/Handwriting/data/db/db_tmp",
        atomset = atomset,
        vocabulary = vocabulary,
        dictionary = dictionary,
        contextmodel = cmgrammar,
        preprocessing = pp,
        topology = topology,
        biokitconfig = None,
        ibisconfig = ibis,
        iterations = 5,
        basemodel = basemodel,
        transcriptkey = "text",
        trainset = fold['trainset'],
        testset = fold['testset'])
    
    
    cvconfigs.append(config)
    

#only create a new cross-validation if necessary
    
cv_is_new = True
cvs = airdb.session.query(db.CrossValidation).all()
for cv in cvs:
    if sorted(list(cv.configurations)) == sorted(cvconfigs):
        print("Cross Validation with given configs already exists")
        cv_is_new = False
        break
if cv_is_new:
    print("Create new Cross Validation")
    crossvalidation = db.CrossValidation()
    crossvalidation.nr_folds = len(cvconfigs)
    crossvalidation.configurations = cvconfigs
    airdb.session.add(crossvalidation)
    airdb.session.commit()

for config in cvconfigs:
    if not config.jobs:
        #alright no job associated with the config, let's create one
        job = db.Job(configuration = config, status = "waiting")
        print(("Adding job with configuration id: %s" % (job.configuration.id, )))
        airdb.session.add(job)
        airdb.session.commit()

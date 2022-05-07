import sys
from . import db
import string
from . import crossval
from sqlalchemy import and_
import argparse

foldbasename = "l25_rh_norp_all"

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
"""
pp = db.get_or_create(airdb.session, db.PreProStandard,
    windowsize = 10,
    frameshift = 10,
    filterstring = "",
    channels = "2 3 4 5 6 7",
    meansub = "",
    feature = "ADC",
    janus_desc = "/project/AMR/Handwriting/flat/featDesc.adcfile.tcl",
    janus_access = "/project/AMR/Handwriting/flat/featAccess.stdprepro.tcl",
    biokit_desc = "stdprepro")
"""
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

cmtype = db.get_or_create(airdb.session, db.ContextModelType,
    name = "grammar")
cmgrammar = db.get_or_create(airdb.session, db.ContextModel,
    name="grammar_alphabet",
    file="/project/AMR/Handwriting/flat/grammar_alphabet.nav",
    type=cmtype)

dictionary = db.get_or_create(airdb.session, db.Dictionary,
    name = "dict_alphabet",
    file = "/project/AMR/Handwriting/flat/dict_alphabet")

vocabulary = db.get_or_create(airdb.session, db.Vocabulary,
    name = "vocab_alphabet",
    file = "/project/AMR/Handwriting/flat/vocab_alphabet")



atomset = db.get_or_create(airdb.session, db.AtomSet,
    name = "alphabet_sil",
    enumeration = (" ".join(string.lowercase))+" SIL")

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
    token_insertion_penalty = 50,
    languagemodel_weight = 0,
    hypo_topn = 4000,
    hypo_beam = 600,
    final_hypo_topn = 50,
    final_hypo_beam = 500,
    lattice_beam = 50)

#trainset = airdb.session.query(db.Dataset).filter(
#    db.Dataset.name=="character_rh_rp_all").one()
#find appropriate base models
# use hardcoded cross validation id = 5
#basecv = airdb.session.query(db.CrossValidation).\
#            filter(db.CrossValidation.id == 5).one()


cvfoldgenerator = retrieve_datasets(airdb.session, foldbasename)
cvconfigs = []
for fold in cvfoldgenerator:
    print("Generating fold")
    train_ids = [x.id for x in fold['trainset'].recordings]
    test_ids = [x.id for x in fold['testset'].recordings]
    config = db.get_or_create(airdb.session, db.Configuration,
        data_basedir = "/project/AMR/Handwriting/data",
        janusdb_name = "/project/AMR/Handwriting/data/db/db_all_rp",
        atomset = atomset,
        vocabulary = vocabulary,
        dictionary = dictionary,
        contextmodel = cmgrammar,
        preprocessing = pp,
        topology = topology,
        biokitconfig = biokit,
        ibisconfig = None,
        iterations = 5,
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

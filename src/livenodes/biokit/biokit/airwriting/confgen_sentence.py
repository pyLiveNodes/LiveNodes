import sys
from . import db
import string
from . import crossval
from sqlalchemy import and_
import argparse



def fixedsetgen(airdb):
    """
    Generate a standard predefined cross validation character eval set.
    """
    testsets = airdb.session.query(db.Dataset).\
                filter(db.Dataset.name.like("testset_kfold_rh_nrp_test_%")).\
                order_by(db.Dataset.name)
    trainsets = airdb.session.query(db.Dataset).\
                 filter(db.Dataset.name.like("trainset_kfold_rh_nrp_test_%")).\
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
                                 "sentence cross validation")
parser.add_argument('database', help="sqlalchemy database string to use")
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

cmtype = db.get_or_create(airdb.session, db.ContextModelType,
    name = "grammar")
cm = db.get_or_create(airdb.session, db.ContextModel,
    name="grammar_alphabet",
    file="/project/AMR/Handwriting/flat/grammar_alphabet.nav",
    type=cmtype)

dictionary = db.get_or_create(airdb.session, db.Dictionary,
    name = "dict_alphabet",
    file = "/project/AMR/Handwriting/flat/dict_alphabet")

vocabulary = db.get_or_create(airdb.session, db.Vocabulary,
    name = "vocab_alphabet",
    file = "/project/AMR/Handwriting/flat/vocab_alphabet")


cmtype_ngram = db.get_or_create(airdb.session, db.ContextModelType,
    name = "ngram")

cm_ngram8k = db.get_or_create(airdb.session, db.ContextModel,
    name="lm_en_3gram_8k",
    file="/project/AMR/Handwriting/lm/English.vocab.en.10k.merg.sel_v2.lm",
    type=cmtype_ngram)

dictionary8k = db.get_or_create(airdb.session, db.Dictionary,
    name = "dict_en_8k_norepos_filler20",
    file = "/project/AMR/Handwriting/vocab/dict.en.10k.merg.norepos.sel_v2.filler20.dec")

vocabulary8k = db.get_or_create(airdb.session, db.Vocabulary,
    name = "vocab_en_8k_norepos",
    file = "/project/AMR/Handwriting/vocab/vocab.en.10k.merg.norepos.sel_v2")


#atomset = db.get_or_create(airdb.session, db.AtomSet,
#    name = "alphabet_sil",
#    enumeration = (" ".join(string.lowercase)) + " SIL")

atomset = db.get_or_create(airdb.session, db.AtomSet,
    name = "alphabet_sil",
    enumeration = (" ".join(string.lowercase)) + " SIL")

topology = db.get_or_create(airdb.session, db.TopologyConfig, 
    hmmstates = 30,
    hmm_repos_states = 10,
    gmm = 6,
    gmm_repos = 2)

ibis = db.get_or_create(airdb.session, db.IbisConfig,
    wordPen = 50,
    lz = 60,
    wordBeam = 1000,
    stateBeam = 1000,
    morphBeam = 1000)

biokit = db.get_or_create(airdb.session, db.BiokitConfig,
    token_insertion_penalty = 50,
    languagemodel_weight = 60,
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

word_trainset = airdb.session.query(db.Dataset).\
                        filter(db.Dataset.name == "words_norp_all").one()
#check for existing models
print("Looking for basemodel:")
word_iterations = 1
char_iterations = 5 
print(("Atomset id: %s" % atomset.id))
print(("Prepro id: %s" % pp.id))
print(("Topology id: %s" % topology.id))
print(("Trainset id: %s" % word_trainset.id))
configs = airdb.session.query(db.Configuration).join(db.Configuration.basemodel).\
                       filter(and_(
                         db.Configuration.data_basedir == "/project/AMR/Handwriting/data",
                         db.Configuration.janusdb_name == '/project/AMR/Handwriting/data/db/db_tmp',
                         db.Configuration.atomset == atomset,
                         db.Configuration.preprocessing == pp,
                         db.Configuration.topology == topology,
                         db.Configuration.transcriptkey == "text",
                         db.Configuration.trainset == word_trainset,
                         db.ModelParameters.iteration == char_iterations)).all()
if len(configs) == 0:
    print("No existing basemodel config found, cannot create config")
    sys.exit(0)
elif len(configs) == 1:
    print(("Found existing config: %s" % configs[0].id))
    basemodel = airdb.session.query(db.ModelParameters).\
        filter(db.ModelParameters.configuration == configs[0]).\
        filter(db.ModelParameters.iteration == word_iterations).one()
else:
    print(("Found %s configurations matching the query:" % (len(configs), )))
    print(configs)
    print("Multiple base configs found, this should not happen")
    sys.exit(0)



cvfoldgenerator = retrieve_datasets(airdb.session, "sen_and_wax_cv_no72")
cvconfigs = []
for fold in cvfoldgenerator:
    train_ids = [x.id for x in fold['trainset'].recordings]
    test_ids = [x.id for x in fold['testset'].recordings]
    config = db.get_or_create(airdb.session, db.Configuration,
        data_basedir = "/home/camma/hwdata",
        janusdb_name = "/project/AMR/Handwriting/data/db/db_sentences",
        atomset = atomset,
        vocabulary = vocabulary8k,
        dictionary = dictionary8k,
        contextmodel = cm_ngram8k,
        preprocessing = pp,
        topology = topology,
        biokitconfig = biokit,
        ibisconfig = None,
        iterations = 5,
        basemodel = basemodel,
        transcriptkey = "reference",
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

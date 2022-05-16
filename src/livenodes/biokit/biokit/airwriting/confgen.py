from . import db
import string


#cross validation fixed set generator
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
        yield {
            'trainset': set[0],
            'testset': set[1],
            'keyval': set[0].name[-3:],
            'nrfolds': nrfolds
        }


def retrieve_datasets(session, basename):
    """
    Retrieves the folds of a cross validation given by the name of the set.
    
    In order to find the datasets, the name must comply with a specific format,
    which is: basename_[test|train]set_fold_<crossvalidation keyval>. 
    """
    testsets = session.query(db.Dataset).\
                filter(db.Dataset.name.like(basename+"_testset_%")).\
                order_by(db.Dataset.name)
    trainsets = session.query(db.Dataset).\
                filter(db.Dataset.name.like(basename+"_trainset_%")).\
                order_by(db.Dataset.name)
    assert (len(testsets) == len(trainsets))
    sets = list(zip(trainsets, testsets))
    nrfolds = len(sets)
    for set in sets:
        yield {
            'trainset': set[0],
            'testset': set[1],
            'keyval': set[0].name[-3:],
            'nrfolds': nrfolds
        }


airdb = db.AirDb("../converted.sqlite")

#Configuration to use

pp = db.get_or_create(
    airdb.session,
    db.PreProStandard,
    windowsize=10,
    frameshift=10,
    filterstring="",
    channels="2 3 4 5 6 7",
    meansub="",
    feature="ADC",
    janus_desc="/project/AMR/Handwriting/flat/featDesc.adis.02.tcl",
    janus_access="/project/AMR/Handwriting/flat/featAccess.adis.01.tcl",
    biokit_desc="stdprepro")

cmtype = db.get_or_create(airdb.session, db.ContextModelType, name="grammar")
cm = db.get_or_create(
    airdb.session,
    db.ContextModel,
    name="grammar_alphabet",
    file="/project/AMR/Handwriting/flat/grammar_alphabet.nav",
    type=cmtype)

dictionary = db.get_or_create(
    airdb.session,
    db.Dictionary,
    name="dict_alphabet",
    file="/project/AMR/Handwriting/flat/dict_alphabet")

vocabulary = db.get_or_create(
    airdb.session,
    db.Vocabulary,
    name="vocab_alphabet",
    file="/project/AMR/Handwriting/flat/vocab_alphabet")

atomset = db.get_or_create(airdb.session,
                           db.AtomSet,
                           name="alphabet",
                           enumeration=(" ".join(string.lowercase)))

topology = db.get_or_create(airdb.session,
                            db.TopologyConfig,
                            hmmstates=30,
                            hmm_repos_states=10,
                            gmm=6,
                            gmm_repos=2)

ibis = db.get_or_create(airdb.session,
                        db.IbisConfig,
                        wordPen=50,
                        lz=60,
                        wordBeam=500,
                        stateBeam=500,
                        morphBeam=500)

biokit = db.get_or_create(airdb.session,
                          db.BiokitConfig,
                          token_insertion_penalty=50,
                          tokensequencemodel_weight=60,
                          hypo_topn=1000,
                          hypo_beam=500,
                          final_node_topn=100,
                          final_node_beam=500,
                          active_node_topn=500,
                          active_node_beam=500)

#trainset = airdb.session.query(db.Dataset).filter(
#    db.Dataset.name=="character_rh_rp_all").one()

cvfoldgenerator = retrieve_datasets(airdb.session, "character_rh_nrp")
cvconfigs = []
for fold in cvfoldgenerator:
    print(fold)
    config = db.get_or_create(
        airdb.session,
        db.Configuration,
        data_basedir="/project/AMR/Handwriting/data",
        janusdb_name="/project/AMR/Handwriting/data/db/db_all_rp",
        atomset=atomset,
        vocabulary=vocabulary,
        dictionary=dictionary,
        contextmodel=cm,
        preprocessing=pp,
        topology=topology,
        ibisconfig=ibis,
        iterations=3,
        transcriptkey="text",
        trainset=fold['trainset'],
        testset=fold['testset'])
    cvconfigs.append(config)
    if not config.jobs:
        #alright no job associated with the config, let's create one
        job = db.Job(configuration=config, status="waiting")
        airdb.session.add(job)
        airdb.session.commit()

crossvalidation = db.CrossValidation()
crossvalidation.nr_folds = len(cvconfigs)
crossvalidation.configurations = cvconfigs
airdb.session.add(crossvalidation)
airdb.session.commit()

print((config.id))

import sys
from . import db
import string
from . import crossval
from sqlalchemy import and_
import argparse

parser = argparse.ArgumentParser(description="Create a configuration for " +
                                 "sentence cross validation")
parser.add_argument('database', help="sqlite database file to use")
args = parser.parse_args()

airdb = db.AirDb(args.database)

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

cmtype_ngram = db.get_or_create(airdb.session,
                                db.ContextModelType,
                                name="ngram")

cm_ngram8k = db.get_or_create(
    airdb.session,
    db.ContextModel,
    name="lm_en_3gram_8k",
    file="/project/AMR/Handwriting/lm/English.vocab.en.10k.merg.sel_v2.lm",
    type=cmtype_ngram)

dictionary8k = db.get_or_create(
    airdb.session,
    db.Dictionary,
    name="dict_en_8k_norepos",
    file="/project/AMR/Handwriting/vocab/dict.en.10k.merg.norepos.sel_v2")

vocabulary8k = db.get_or_create(
    airdb.session,
    db.Vocabulary,
    name="vocab_en_8k_norepos",
    file="/project/AMR/Handwriting/vocab/vocab.en.10k.merg.norepos.sel_v2")

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
                          hypo_topn=10,
                          hypo_beam=100,
                          final_node_topn=300,
                          final_node_beam=100,
                          active_node_topn=10000,
                          active_node_beam=300)

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
word_iterations = 3
configs = airdb.session.query(db.Configuration).\
                       filter(and_(
                         db.Configuration.data_basedir == "/project/AMR/Handwriting/data",
                         db.Configuration.janusdb_name == '/project/AMR/Handwriting/data/db/db_tmp',
                         db.Configuration.atomset == atomset,
                         db.Configuration.preprocessing == pp,
                         db.Configuration.topology == topology,
                         db.Configuration.transcriptkey == "text",
                         db.Configuration.trainset == word_trainset)).all()
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



trainset = airdb.session.query(db.Dataset).\
                        filter(db.Dataset.name == "set_all_sentences").one()
config = db.get_or_create(
    airdb.session,
    db.Configuration,
    data_basedir="/project/AMR/Handwriting/data",
    janusdb_name="/project/AMR/Handwriting/data/db/db_sentences",
    atomset=atomset,
    vocabulary=vocabulary8k,
    dictionary=dictionary8k,
    contextmodel=cm_ngram8k,
    preprocessing=pp,
    topology=topology,
    biokitconfig=biokit,
    ibisconfig=None,
    iterations=5,
    basemodel=basemodel,
    transcriptkey="reference",
    trainset=trainset)

if not config.jobs:
    #alright no job associated with the config, let's create one
    job = db.Job(configuration=config, status="waiting")
    print(("Adding job with configuration id: %s" % (job.configuration.id, )))
    airdb.session.add(job)
    airdb.session.commit()

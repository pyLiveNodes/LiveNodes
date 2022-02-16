from . import db
import string

import argparse

parser = argparse.ArgumentParser(description="Create a configuration for "+
                                 "word training")
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

atomset = db.get_or_create(airdb.session, db.AtomSet,
    name = "alphabet_sil",
    enumeration = (" ".join(string.lowercase)) + " SIL")

topology = db.get_or_create(airdb.session, db.TopologyConfig, 
    hmmstates = 30,
    hmm_repos_states = 10,
    gmm = 6,
    gmm_repos = 2)

# strictly, neither a grammar, dictionary or vocab is necessary for training
# but the old tcl scripts demand for, so we give it to them

cmgrammar = db.get_or_create(airdb.session, db.ContextModelType,
    name = "grammar")

# word specific config
cm_words = db.get_or_create(airdb.session, db.ContextModel,
    name = "grammar_top99",
    file = "/project/AMR/Handwriting/flat/grammar_top99.nav",
    type = cmgrammar)
dict_words = db.get_or_create(airdb.session, db.Dictionary,
    name = "dict_top99_norepo",
    file = "/project/AMR/Handwriting/flat/dict_top99_norepo")
vocab_words = db.get_or_create(airdb.session, db.Vocabulary,
    name = "vocab_top99",
    file = "/project/AMR/Handwriting/flat/vocab_top99")



#trainset = airdb.session.query(db.Dataset).filter(
#    db.Dataset.name=="character_rh_rp_all").one()

trainset = airdb.session.query(db.Dataset).\
                        filter(db.Dataset.name == "words_norp_all").one()

#check for existing models
iteration = 5 
baseconfig_id = 1
basemodel = airdb.session.query(db.ModelParameters).\
                       filter_by(configuration_id = baseconfig_id).\
                       filter_by(iteration = iteration).one()
print(("Found specified pretrained model: %s" % (basemodel,)))


config = db.get_or_create(airdb.session, db.Configuration,
        data_basedir = "/project/AMR/Handwriting/data",
        janusdb_name = "/project/AMR/Handwriting/data/db/db_tmp",
        atomset = atomset,
        vocabulary = vocab_words,
        dictionary = dict_words,
        contextmodel = cm_words,
        preprocessing = pp,
        topology = topology,
        iterations = 5,
        transcriptkey = "text",
        trainset = trainset,
        basemodel = basemodel)
if not config.jobs:
        #alright no job associated with the config, let's create one
        job = db.Job(configuration = config, status = "waiting")
        airdb.session.add(job)
        airdb.session.commit()

airdb.session.commit()
    

print(("Configuration id: %s" % (config.id,) ))

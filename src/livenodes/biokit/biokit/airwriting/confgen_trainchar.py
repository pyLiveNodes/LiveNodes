from . import db
import string
import argparse

parser = argparse.ArgumentParser(description="Create a configuration for " +
                                 "character training")
parser.add_argument('database',
                    help="sqlalchemy database connection string to use")
args = parser.parse_args()

airdb = db.AirDb(args.database)

#Configuration to use
#janus_desc = "/project/AMR/Handwriting/flat/featDesc.adis.02.tcl",
#janus_access = "/project/AMR/Handwriting/flat/featAccess.adis.01.tcl",
#janus_desc = "/project/AMR/Handwriting/flat/featDesc.adcfile.tcl",
#janus_access = "/project/AMR/Handwriting/flat/featAccess.stdprepro.tcl",
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

atomset = db.get_or_create(airdb.session,
                           db.AtomSet,
                           name="alphabet_sil",
                           enumeration=(" ".join(string.lowercase)) + " SIL")

topology = db.get_or_create(airdb.session,
                            db.TopologyConfig,
                            hmmstates=30,
                            hmm_repos_states=10,
                            gmm=6,
                            gmm_repos=2)

# strictly, neither a grammar, dictionary or vocab is necessary for training
# but the old tcl scripts demand for, so we give it to them

cmgrammar = db.get_or_create(airdb.session,
                             db.ContextModelType,
                             name="grammar")
cm = db.get_or_create(
    airdb.session,
    db.ContextModel,
    name="grammar_alphabet",
    file="/project/AMR/Handwriting/flat/grammar_alphabet.nav",
    type=cmgrammar)

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


trainset = airdb.session.query(db.Dataset).\
                        filter(db.Dataset.name == "l25_rh_norp_all").one()

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
    iterations=10,
    transcriptkey="text",
    trainset=trainset)
if not config.jobs:
    #alright no job associated with the config, let's create one
    job = db.Job(configuration=config, status="waiting")
    airdb.session.add(job)
    airdb.session.commit()

airdb.session.commit()

print(("Configuration id: %s" % (config.id, )))

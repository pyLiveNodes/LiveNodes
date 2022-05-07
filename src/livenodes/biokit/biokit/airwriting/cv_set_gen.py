from . import db
from . import crossval
import argparse
import crossvalidation

parser = argparse.ArgumentParser(description="Create some standard data sets")
parser.add_argument('database', help="sqlalchem compatible database uri")
args = parser.parse_args()

airdb = db.AirDb(args.database)

seed = 1234

char = True
word = True
sen = True
wax = True
wax_no072 = True
sen_and_wax_no72 = True

if char:
    print("generating character datasets")

    dataset_file = "/project/AMR/Handwriting/data/sets/l25_rh_rp_all.set"
    airdb.load_janus_dataset(dataset_file, "l25_rh_norp_all")

    #retrieve the created dataset from db and make cross-val sets
    charset = airdb.session.query(
        db.Dataset).filter_by(name="l25_rh_norp_all").one()
    charlist = [[r.id, r.experiment.string_id, r] for r in charset.recordings]
    cv = crossvalidation.CrossValidation(seed)
    cvgen = cv.createPerKeyCrossvalidation(charlist, 1)
    for fold in cvgen:
        trainset = db.Dataset()
        trainset.name = "%s_trainset_fold_%s" % (charset.name,
                                                 fold['keyValue'])
        trainset.recordings = [x[2] for x in fold['train']]
        airdb.insert_unique(trainset)
        testset = db.Dataset()
        testset.name = "%s_testset_fold_%s" % (charset.name, fold['keyValue'])
        testset.recordings = [x[2] for x in fold['test']]
        airdb.insert_unique(testset)

if word:
    print("generating word datasets")

    wordset_file = "/project/AMR/Handwriting/data/sets/allwords.set"
    airdb.load_janus_dataset(wordset_file, "words_norp_all")

    #retrieve the created dataset from db and make cross-val sets
    wordset = airdb.session.query(
        db.Dataset).filter_by(name="words_norp_all").one()
    wordlist = [[r.id, r.experiment.string_id, r] for r in wordset.recordings]
    cv = crossvalidation.CrossValidation(seed)
    cvgen = cv.createPerKeyCrossvalidation(wordlist, 1)
    for fold in cvgen:
        trainset = db.Dataset()
        trainset.name = "%s_trainset_fold_%s" % (wordset.name,
                                                 fold['keyValue'])
        trainset.recordings = [x[2] for x in fold['train']]
        airdb.insert_unique(trainset)
        testset = db.Dataset()
        testset.name = "%s_testset_fold_%s" % (wordset.name, fold['keyValue'])
        testset.recordings = [x[2] for x in fold['test']]
        airdb.insert_unique(testset)

if sen:
    print("generating sentence datasets")

    wordset_file = "/project/AMR/Handwriting/data/sets/set_all_sentences"
    airdb.load_janus_dataset(wordset_file, "set_all_sentences")

    basename = "sentence_cv_all"

    #generate subquery which includes all data to generate sets from
    subq = airdb.session.query(db.Recording.id, db.Experiment.string_id,
                db.Person.name).join(db.Experiment).join(db.Person).filter(
                db.Experiment.string_id.in_(
                ["053", "054", "055", "056", "057", "058", "059", "060", "061"])).\
                subquery()

    #REMARK: Using different crossval class than above, has slightly different API

    cv = crossval.CrossValidation(airdb.session, seed)
    cvfoldgenerator = cv.getPerKeyCrossValidationFolds('string_id', subq)

    for fold in cvfoldgenerator:
        # trainset
        trainids = [x.id for x in fold['trainSet']]
        recordings = airdb.session.query(db.Recording).\
                        filter(db.Recording.id.in_(trainids)).all()
        dataset = db.Dataset()
        dataset.name = basename + "_trainset_fold_" + fold['keyval']
        dataset.recordings = recordings
        airdb.insert_unique(dataset)
        # testset
        testids = [x.id for x in fold['testSet']]
        recordings = airdb.session.query(db.Recording).\
                        filter(db.Recording.id.in_(testids)).all()
        dataset = db.Dataset()
        dataset.name = basename + "_testset_fold_" + fold['keyval']
        dataset.recordings = recordings
        airdb.insert_unique(dataset)

if wax:
    print("generating wax datasets")

    wordset_file = "/project/AMR/Handwriting/data/sets/set_all_wax"
    airdb.load_janus_dataset(wordset_file, "set_all_wax")

    basename = "wax_cv_all"

    #generate subquery which includes all data to generate sets from
    subq = airdb.session.query(db.Recording.id, db.Experiment.string_id,
                db.Person.name).join(db.Experiment).join(db.Person).filter(
                db.Experiment.string_id.in_(
                ["070", "071", "072", "073", "074", "075", "076", "077"])).\
                subquery()

    #REMARK: Using different crossval class than above, has slightly different API

    cv = crossval.CrossValidation(airdb.session, seed)
    cvfoldgenerator = cv.getPerKeyCrossValidationFolds('string_id', subq)

    for fold in cvfoldgenerator:
        # trainset
        trainids = [x.id for x in fold['trainSet']]
        recordings = airdb.session.query(db.Recording).\
                        filter(db.Recording.id.in_(trainids)).all()
        dataset = db.Dataset()
        dataset.name = basename + "_trainset_fold_" + fold['keyval']
        dataset.recordings = recordings
        airdb.insert_unique(dataset)
        # testset
        testids = [x.id for x in fold['testSet']]
        recordings = airdb.session.query(db.Recording).\
                        filter(db.Recording.id.in_(testids)).all()
        dataset = db.Dataset()
        dataset.name = basename + "_testset_fold_" + fold['keyval']
        dataset.recordings = recordings
        airdb.insert_unique(dataset)

if wax_no072:
    print("generating wax datasets without 072")

    wordset_file = "/project/AMR/Handwriting/data/sets/set_all_wax"
    airdb.load_janus_dataset(wordset_file, "set_all_wax")

    basename = "wax_cv_no72"

    #generate subquery which includes all data to generate sets from
    subq = airdb.session.query(db.Recording.id, db.Experiment.string_id,
                db.Person.name).join(db.Experiment).join(db.Person).filter(
                db.Experiment.string_id.in_(
                ["070", "071", "073", "074", "075", "076", "077"])).\
                subquery()

    #REMARK: Using different crossval class than above, has slightly different API

    cv = crossval.CrossValidation(airdb.session, seed)
    cvfoldgenerator = cv.getPerKeyCrossValidationFolds('string_id', subq)

    for fold in cvfoldgenerator:
        # trainset
        trainids = [x.id for x in fold['trainSet']]
        recordings = airdb.session.query(db.Recording).\
                        filter(db.Recording.id.in_(trainids)).all()
        dataset = db.Dataset()
        dataset.name = basename + "_trainset_fold_" + fold['keyval']
        dataset.recordings = recordings
        airdb.insert_unique(dataset)
        # testset
        testids = [x.id for x in fold['testSet']]
        recordings = airdb.session.query(db.Recording).\
                        filter(db.Recording.id.in_(testids)).all()
        dataset = db.Dataset()
        dataset.name = basename + "_testset_fold_" + fold['keyval']
        dataset.recordings = recordings
        airdb.insert_unique(dataset)

if sen_and_wax_no72:
    print("generating combined sentence and wax datasets without 072")

    #wordset_file = "/project/AMR/Handwriting/data/sets/set_all_wax"
    #airdb.load_janus_dataset(wordset_file, "set_all_sen_and_wax")

    basename = "sen_and_wax_cv_no72"

    #generate subquery which includes all data to generate sets from
    subq = airdb.session.query(db.Recording.id, db.Experiment.string_id,
                db.Person.name).join(db.Experiment).join(db.Person).filter(
                db.Experiment.string_id.in_(
                ["053", "054", "055", "056", "057", "058", "059", "060", "061", "070", "071", "073", "074", "075", "076", "077"])).\
                subquery()

    #REMARK: Using different crossval class than above, has slightly different API

    cv = crossval.CrossValidation(airdb.session, seed)
    cvfoldgenerator = cv.getPerKeyCrossValidationFolds('string_id', subq)

    for fold in cvfoldgenerator:
        # trainset
        trainids = [x.id for x in fold['trainSet']]
        print(trainids)
        #recordings = airdb.session.query(db.Recording).\
        #                filter(db.Recording.id.in_(trainids)).all()
        recordings = [
            airdb.session.query(
                db.Recording).filter(db.Recording.id == x).one()
            for x in trainids
        ]
        dataset = db.Dataset()
        dataset.name = basename + "_trainset_fold_" + fold['keyval']
        dataset.recordings = recordings
        airdb.insert_unique(dataset)
        # testset
        testids = [x.id for x in fold['testSet']]
        recordings = airdb.session.query(db.Recording).\
                        filter(db.Recording.id.in_(testids)).all()
        dataset = db.Dataset()
        dataset.name = basename + "_testset_fold_" + fold['keyval']
        dataset.recordings = recordings
        airdb.insert_unique(dataset)

airdb.session.commit()

"""
Generate a list importable by populate.jdb for the wax sentences
"""

from . import db

dbfile = "/project/AMR/Handwriting/data/db/airwriting_dev_charwordssenwax.sqlite"

airdb = db.AirDb(dbfile)

recs = airdb.session.query(db.Recording).join(db.Experiment).filter(db.Experiment.string_id.in_(["070", "071", "072", "073", "074", "075", "076", "077"])).all()
#print csv as key value pairs
id = 801
for r in recs:
    print(('{name {%s}} {reference {%s}} {basedir {%s}} {stringId {v%s}} {filename {%s}} {id {%s}}' % (
        r.experiment.person.name,
        r.reference,
        r.experiment.base_dir,
        r.experiment.string_id,
        r.filename,
        id
        )))
    id = id + 1


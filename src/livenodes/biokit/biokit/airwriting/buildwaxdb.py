
from . import AirwritingDb
import os

basedir = "/project/AMR/Handwriting/data/sentence/wax9transform_multiple/"

exp = [("v070", "marcus"),
       ("v071", "renata"),
       ("v072", "markus"),
       ("v073", "nina"),
       ("v074", "fabian"),
       ("v075", "marlene"),
       ("v076", "mark"),
       ("v077", "jing")]
    

airdb = AirwritingDb.AirwritingDb()
#airdb.create("/project/AMR/Handwriting/data/db/dbwax_oldstyle.sqlite")
airdb.open("/project/AMR/Handwriting/data/db/dev.sentences.transform.multiple.sqlite")
for ex in exp:
    airdb.addExperimentFromDirectory(ex[1], 
                                     ex[0],
                                     os.path.join(basedir, ex[0]+"/data"),
                                     "adc")

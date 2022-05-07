# coding: utf-8
from airwriting import db

adb = db.AirDb("converted.sqlite")
jdb = db.JanusDb("/project/AMR/Handwriting/data/db/all.sqlite")
jdb.insert_into_airdb(adb, "AMR/Handrwiting/data")

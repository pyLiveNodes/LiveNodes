import os
from . import waxtoib

sourcedir = "/project/AMR/Handwriting/data/sentence/wax9recordings/"
targetdir = "/project/AMR/Handwriting/data/sentence/wax9transform_multiple/"

wax2ib = waxtoib.WaxToIb()

for dirpath, dirnames, filenames in os.walk(sourcedir):
    print(dirpath)
    for fname in filenames:
        suffix = os.path.splitext(fname)[1]
        if suffix == ".adc":
            relpath = os.path.relpath(dirpath, sourcedir)
            if not os.path.exists(os.path.join(targetdir, relpath)):
                os.makedirs(os.path.join(targetdir, relpath))
            sourcefile = os.path.join(dirpath, fname)
            targetfile = os.path.join(targetdir, relpath, fname)
            print(("convert %s to %s" % (sourcefile, targetfile)))
            wax2ib.convertfile(sourcefile, targetfile)



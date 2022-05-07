import BioKIT
from . import airwritingUtil
import align
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="compute results from csv file")
    parser.add_argument("resfile", help="file containing results in csv format")
    args = parser.parse_args()
    
    refkey = "reference"
    hypokey = "hypothesis"
 
    resfile = args.resfile
    with open(resfile, "r") as resultfh:
        resultslist = airwritingUtil.readResultFile(resultfh)
        ter = align.totalTokenErrorRate(resultslist, refkey, hypokey)
        print(("Token Error Rate: " + str(ter)))


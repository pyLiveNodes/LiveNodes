# -*- coding: utf8 -*-

import os
import pickle

# Main program
if __name__ == '__main__':
    minCvIndex = 2
    maxCvIndex = 5
    hierarchical = 1
    
    deletions = dict()
    insertions = dict()
    substitutions = dict()
    #TODO extend to insertions,substitutions
    folders = os.listdir('.')
    for folder in folders:
        if (os.path.isdir(folder) and folder.count('12Gauss4') > 0):
            os.chdir(folder)
            if (hierarchical > 0):
                os.chdir('test')
            print("We are now in folder " + str(folder))
            for cvIndex in range(minCvIndex, maxCvIndex+1):
                for subFolder in os.listdir('.'):
                    #TODO distinguish between cv1 and cv10
                    if (os.path.isdir(subFolder) and subFolder.count('lmw20_tip20_masterBeam1_cv'+str(cvIndex)) > 0):
                        settings = subFolder[:len(subFolder)-len(str(cvIndex))-2]
                        print("settings are "+ str(settings))
                        #TODO Iterate over testIterations
                        #TODO Check if file does exist
                        if (cvIndex == minCvIndex):
                            file = open(subFolder+'/deletionsIter3')
                            deletions[settings] = pickle.load(file)
                            file.close()
                        else:
                            file = open(subFolder+'/deletionsIter3')
                            tempDeletions = pickle.load(file)
                            file.close()
                            #TODO Append results from additional folds
                            #TODO extend results filename with minCv, maxCv
            if (hierarchical > 0):
                os.chdir('..')
            for settings in deletions:
                file = open("crossValidationDeletions"+str(settings)+"Iter3", 'w')
                pickle.dump(deletions[settings], file)
                file.close()
            os.chdir('..')

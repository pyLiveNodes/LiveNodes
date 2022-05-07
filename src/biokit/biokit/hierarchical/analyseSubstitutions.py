# -*- coding: utf8 -*-

import pickle

# python-lib
import align

def storeSubstitution(substitutions, currentReferenceToken, currentHypoToken, frequency):
    if (not currentReferenceToken in substitutions):
        substitutions[currentReferenceToken] = dict()
    if (not currentHypoToken in substitutions[currentReferenceToken]):
        substitutions[currentReferenceToken][currentHypoToken] = frequency
    else:
        substitutions[currentReferenceToken][currentHypoToken] = substitutions[currentReferenceToken][currentHypoToken] + frequency
    return substitutions

def printDetails(errorMap, index):
    for side in errorMap[index]:
        for key in errorMap[index][side]: 
            print("Current side is " + str(side))
            for value in errorMap[index][side][key]:
                print(str(key) + " -> " + str(value) + ": " + str(errorMap[index][side][key][value]))

# Main program
if __name__ == '__main__':
    useSubstitutions = True
    
    fileName = 'substitutionsIter3'
    
    if (useSubstitutions == True):
        file = open(fileName)
        substitutions = pickle.load(file)
        file.close()
    else:
        substitutions = []
        for fromStream in range(3): #For each stream
            substitutions.append([])
            for toStream in range(3): #For each stream
                substitutions[fromStream].append([])
                for index in range(2): #For each finest stream
                    substitutions[fromStream][toStream].append(dict())
        
        hyposFileName = 'Hypos_Iter3.trn'
        refsFileName =  'Refs_Iter3.trn'
        
        refsFile = open(refsFileName)
        hyposFile = open(hyposFileName)
        
        refsLine = refsFile.readline()
        hyposLine = hyposFile.readline()
        while (refsLine != ''):
            
             cleanedString = hyposLine.split('(')[0]
            
             cleanedString = align.separatePrimitives(cleanedString)

             cleanedString = align.normalizeSequence(cleanedString)
            
             #log("Info", "normalized hypo was: " + cleanedString)
            
             cleanedString = align.combineAction(cleanedString, "wait")
             cleanedString = align.combineAction(cleanedString, "hold")
             cleanedString = align.combineAction(cleanedString, "stirr")
             cleanedString = align.combineAction(cleanedString, "shift")
             cleanedString = align.combineAction(cleanedString, "cut")
             cleanedString = align.combineAction(cleanedString, "smear")
            
#             log("Info", "combined hypo was: " + cleanedString)

            
             reference = refsLine.split('(')[0]
            #log("Info", "reference was: " + reference)
             reference = reference.lower()
            
            #Writing hypo to trn file
             reference = align.separatePrimitives(reference)
                        #log("Info", "separated reference was: " + reference)
            
             reference = align.normalizeSequence(reference)
            
            #log("Info", "normalized reference was: " + reference)
            
             reference = align.combineAction(reference, "wait")
             reference = align.combineAction(reference, "hold")
             reference = align.combineAction(reference, "stirr")
             reference = align.combineAction(reference, "shift")
             reference = align.combineAction(reference, "cut")
             reference = align.combineAction(reference, "smear")
            
#             log("Info", "combined reference was: " + reference)
     
            #get error rate
#            [errorCount, referenceAtFinestStream, hypoAtFinestStream, alignedSequences, insDelSubCounts, insDelSubErrors] = align.alignHierarchicalWithPenalties(reference, cleanedString, MotionHierarchical.penalties[0], MotionHierarchical.penalties[1], MotionHierarchical.penalties[2])
             [tokenErrorRate, referenceAtFinestStream, hypoAtFinestStream, alignedSequences, insDelSubCounts, insDelSubErrors] = align.tokenErrorRateHierarchical(reference, cleanedString)
             for fromStream in range(len(insDelSubErrors[2])):
                for toStream in range(len(insDelSubErrors[2][fromStream])):
                    for dimension in range(len(insDelSubErrors[2][fromStream][toStream])):
                        for tempReference in insDelSubErrors[2][fromStream][toStream][dimension]:
                            for tempHypo in insDelSubErrors[2][fromStream][toStream][dimension][tempReference]:
                                substitutions[fromStream][toStream][dimension] = storeSubstitution(substitutions[fromStream][toStream][dimension], tempReference, tempHypo, insDelSubErrors[2][fromStream][toStream][dimension][tempReference][tempHypo])
            
            
             #Skip empry lines
             refsLine = refsFile.readline()
             hyposLine = hyposFile.readline()
             
             #Read next line with sequence
             refsLine = refsFile.readline()
             hyposLine = hyposFile.readline()
    
        fp = open(fileName, 'w')
        pickle.dump(substitutions, fp)
        fp.close()

        
    
    print('Analyse substitutions')
    errors = dict()
    bpErrors = dict()
    errorMap = []
    for i in range(9):
        errors[i] = 0
        bpErrors[i] = dict()
	errorMap.append(dict())

    for fromStream in range(len(substitutions)):
        print('Stream: ', fromStream)
        for toStream in range(len(substitutions[fromStream])):
            print('Stream (from -> to): ', fromStream, '->', toStream)
            print('  Substitutions')
            for dimension in range(len(substitutions[fromStream][toStream])):
                print('Dimension ', dimension)
                for key in substitutions[fromStream][toStream][dimension]:
                    for value in substitutions[fromStream][toStream][dimension][key]:
                        amount = substitutions[fromStream][toStream][dimension][key][value]
                        splittedKey = key.split('_')
                        splittedValue = value.split('_')
                                
                        print("bp is: " + splittedKey[2])
                        if (splittedKey[2] == 'wholearm' or splittedValue[2] == 'wholearm'):
                            errorValue = 0.5
                            amount /= 2.0
                        else:
                            errorValue = 1
                        
                        for index in range(1, len(splittedKey) - 1 ):
                            if (splittedKey[index] != splittedValue[index]):
#                            print 'index ' + str(index) + ' key ' + str(splittedKey[index]) + ' value ' + str(splittedValue[index])
                                if splittedKey[3] not in errorMap[index]:
                                    errorMap[index][splittedKey[3]] = dict()
                                if splittedKey[index] not in errorMap[index][splittedKey[3]]:
                                	errorMap[index][splittedKey[3]][splittedKey[index]] = dict()

                                    
                                if splittedValue[index] not in errorMap[index][splittedKey[3]][splittedKey[index]]:
                                	errorMap[index][splittedKey[3]][splittedKey[index]][splittedValue[index]] = errorValue
                                else:
                                	errorMap[index][splittedKey[3]][splittedKey[index]][splittedValue[index]] = errorMap[index][splittedKey[3]][splittedKey[index]][splittedValue[index]] + errorValue
                            
                                if splittedKey[3] not in bpErrors[index-1]:
                                    bpErrors[index-1][splittedKey[3]] = amount
                                else:
                                    bpErrors[index-1][splittedKey[3]] += amount 
                                errors[index - 1] += amount

    printDetails(errorMap, 1)
#    printDetails(errorMap, 3)
#    printDetails(errorMap, 4)
#    printDetails(errorMap, 6)
#    printDetails(errorMap, 7)
    
    for bp in ['right', 'center', 'left']:
        print('BodyPart ' + str(bp) + ': ')
        print('action has ' + str(bpErrors[0][bp]) + ' errors')
        print('bodyPart has ' + str(bpErrors[1][bp]) + ' errors')
        print('side has ' + str(bpErrors[2][bp]) + ' errors')
        print('dirObject has ' + str(bpErrors[3][bp]) + ' errors')
        print('indirObject has ' + str(bpErrors[4][bp]) + ' errors')
        print('target has ' + str(bpErrors[5][bp]) + ' errors')
        print('position has ' + str(bpErrors[6][bp]) + ' errors')
        print('direction has ' + str(bpErrors[7][bp]) + ' errors')
        print('')


                             
    print('action has ' + str(errors[0]) + ' errors')
    print('bodyPart has ' + str(errors[1]) + ' errors')
    print('side has ' + str(errors[2]) + ' errors')
    print('dirObject has ' + str(errors[3]) + ' errors')
    print('indirObject has ' + str(errors[4]) + ' errors')
    print('target has ' + str(errors[5]) + ' errors')
    print('position has ' + str(errors[6]) + ' errors')
    print('direction has ' + str(errors[7]) + ' errors')
    print('sequenceType has ' + str(errors[8]) + ' errors')

# -*- coding: utf8 -*-

import argparse
import math

# python-lib
import align
from . import MotionDb
from .MotionDb import *

from . import Segmentation
from .Segmentation import *

def lmAccu ( text ):
  lm['cnt'] += len(text)
  lm[1]['</s>'] += 1
  v = text[0]
  for x in range(1, len(text)):
    w = text[x]
    q = v+','+w
    #Count unigrams
    if not v in lm[1]: 
        lm[1][v] = 1
        lm['m'] += 1
    else:
        lm[1][v] += 1
    
    #Count bigrams
    if not (q in lm[2]):
        lm[2][q] = 1
        lm['b'] += 1
    else:
        lm[2][q] += 1
    v = w
    
def lmUpdate(): 
    disc =  0.01
    lm['p'] = dict()
    for i in lm[1]:
        lm['p'][i] = math.log((lm[1][i]-disc)/lm['cnt']) /2.30259
    for i in lm[2]:
        tokens = i.split(',')
        lm['p'][i] = math.log((lm[2][i]-disc)/lm[1][tokens[0]])/2.30259
    if (createConcurrentTrigrams > 0):
            #Code for concurrent trigram
            for i in lm[3]:
                tokens = i.split(',')
                lm['p'][i] = math.log((lm[3][i]-disc)/lmConcurrent[2][tokens[0]+','+tokens[1]])/2.30259

def lmWrite ( filename ):
  f = open(filename, 'w')
  mlist = []
  blist = []
  tlist = []

  if (createConcurrentTrigrams > 0):
    for i in lm[3]:
        tokens = i.split(',')
        if tokens[0].lower() not in lm[1]:
            lm[1][tokens[0].lower()] = 1
            lm['p'][tokens[0].lower()] = -100
            lm['m'] += 1
        if (tokens[0]+','+tokens[1]) not in lm[2]:
            lm[2][tokens[0].lower()+','+tokens[1].lower()] = 1
            lm['p'][tokens[0].lower()+','+tokens[1].lower()] = -100
            lm['b'] += 1
        tlist.append(tokens[0].lower() + ' ' + tokens[1].lower() + ' ' + tokens[2].lower() + ' ' + str(lm['p'][i]))
    tlist.sort()

  for i in lm[1]:
    mlist.append(i + ' ' + str(lm['p'][i]) + ' 0.0')
  for i in lm[2]:
    tokens = i.split(',')
    bigramString = tokens[0] + ' ' + tokens[1] + ' ' + str(lm['p'][i])
    if (createConcurrentTrigrams > 0):
        bigramString += ' 0.0'
    blist.append(bigramString)

      
  mlist.sort()
  blist.sort()
  
  f.write("\\data\\\nngram 1="+str(lm['m']) + "\nngram 2="+str(lm['b']))
  if (createConcurrentTrigrams > 0):
    f.write("\nngram 3="+str(lm['t']))
  f.write("\n\n\\1-grams:\n")
  for m in mlist:
      splittedM = m.split()
      f.write(splittedM[1] + " " + splittedM[0] + " " + splittedM[2] + "\n") 
  f.write("\n\\2-grams:\n")
  for b in blist:
      splittedB = b.split()
      f.write(splittedB[2] + " " + splittedB[0] + " " + splittedB[1])
      if (createConcurrentTrigrams > 0):
          f.write(" " + splittedB[3])
      f.write("\n")
  if (createConcurrentTrigrams > 0):
      f.write("\n\\3-grams:\n")
      for t in tlist:
          splittedT = t.split()
          f.write(splittedT[3] + " " + splittedT[0] + " " + splittedT[1] + " " + splittedT[2] +"\n")
 
  f.write("\\end\\")
  f.close()

if __name__ == '__main__':
        
        addDir = ""
    
        parser = argparse.ArgumentParser(description='Create bigram tokensequence model')
        
        parser.add_argument('--cvIndex', default=-1,
                    type=int, help='index for the current cross validation fold (-1 = no cross validation)')
        parser.add_argument('--addDir', help='Additional path prefix')
        parser.add_argument('--folds', type=int, help='Number of crossvalidation folds')
        parser.add_argument('--createConcurrentTrigrams', default=0, type=int, help='create trigrams with predecessor of concurrent primitive')
        parser.add_argument('--segFolder', default="")
        
        
        args = vars(parser.parse_args())

        cvIndex = args['cvIndex']
        addDir = args['addDir']
        createConcurrentTrigrams = args['createConcurrentTrigrams']
        segFolder = args['segFolder']
    
        #Number of folds for the cross-validation
        folds = args['folds']
        #Database entry which is balanced between the cross-validation folds
        key = 'sequenceVariant' #TODO duplicate to createMotionDatabase.py
        
        database = MotionDb()
        database.open(addDir+'../../data/motionDataBase.db')
        
        #TODO change to dynamic
        topology = {'whole_body': ['left_arm', 'right_arm']}
        segmentation = Segmentation(topology)
                
        cvSequences = database.retrieveBalancedCrossValidationSets(key, folds)

        #TODO Ugly code to retrieve the number of finest stream to iterate over
        dbInfos = database.getTranscripts(cvSequences, 0)
        skip = False   
        for info in dbInfos:
            if (skip == False):
                splittedSequence = info['transcript'].split()
                skip = True

        [numberOfStreams, numberOfSubStreams, numberOfFinestStreams, firstSubStreamIndex] = align.retrieveHierarchy(splittedSequence)
        finestStreamCount = numberOfFinestStreams[0]
        #End of ugly code
        
        for streamIndex in range(numberOfFinestStreams[0]):
        
            #Initialize tokensequence model
            lm = dict()
            lmConcurrent = dict() #Stores bigrams of concurrent primitives
            lm['cnt'] = 0 #Number of tokens
            lm['m'] = 1 #Number of unique tokens / unigrams
            lm['b'] = 0  #Number of unique bigrams
            lm['t'] = 0
            lm[1] = dict()
            lm[2] = dict()
            lm[3] = dict()
            lmConcurrent[2] = dict()
            lm[1]['</s>'] = 0 # Special treatment of final token, which is skipped in lmAcuu 
            
            for index in range(folds):
                if (index != (cvIndex - 1)):
                    dbInfos = database.getTranscripts(cvSequences, index)
                    
                    for info in dbInfos:
                        sequence = info['transcript'].lower()
                        splittedReference = sequence.split()
                        
                        referenceSubStream = [ [] for col in range(finestStreamCount) ]
                        referenceStreamIndices = [ [] for col in range(finestStreamCount) ]

                        align.retrieveFinestStreamRepresentation(0, firstSubStreamIndex, splittedReference, referenceSubStream, referenceStreamIndices, numberOfSubStreams, numberOfFinestStreams)

                        # accumulate tokensequence model 
                        referenceSubStream[streamIndex].insert(0, '<s>')
                        referenceSubStream[streamIndex].append('</s>')
                        
                        lmAccu(referenceSubStream[streamIndex])
                    if (createConcurrentTrigrams > 0):
                        # Code for concurrent trigram lm
                        for cvSequence in cvSequences[index]:
                            #TODO Change to dynamic value
                            fileName = str(segFolder) + "/Felix/Ruehrei/" + str(cvSequence) + ".xml"
                            
                            print("segmentation fileName is: " + str(cvSequence))
                            segmentation.loadFile(fileName)
                            tmpLm = dict()
                            [tmpLm[3],tmpLm[2]] = segmentation.getConcurrentTrigrams(streamIndex)
                            for trigram in tmpLm[3]:
                                if trigram not in lm[3]:
                                    lm['t'] += 1
                                    lm[3][trigram] = tmpLm[3][trigram]
                                else:
                                    lm[3][trigram] += tmpLm[3][trigram]
                            for concurrentBigram in tmpLm[2]:
                                if concurrentBigram not in lmConcurrent[2]:
                                    lmConcurrent[2][concurrentBigram] = tmpLm[2][concurrentBigram]
                                else:
                                    lmConcurrent[2][concurrentBigram] += tmpLm[2][concurrentBigram]

                    
            #update tokensequence model
            lmUpdate()
            
            if (createConcurrentTrigrams > 0):
                lmWrite(addDir+"../../data/langmodConcurrentTrigram_cv"+str(cvIndex)+"_stream"+str(streamIndex))
            else:
                #write tokensequence model to file
                lmWrite(addDir+"../../data/langmodBigram_cv"+str(cvIndex)+"_stream"+str(streamIndex))



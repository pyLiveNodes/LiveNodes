import math

# python lib
import logger
from logger import log

import BioKIT
from BioKIT import *


###
### TODO: short description
###
def getGlobalVarianceSequence(fs):
        targetVectorSequence=fs
        varianceVector=NumericVector(fs.getDimensionality())
        meanVector=NumericVector(fs.getDimensionality())
        for t in range(0,targetVectorSequence.getLength()):
            meanVector+=targetVectorSequence.getFeatureVector(t).getVector()

        meanVector/=targetVectorSequence.getLength()
        for t in range(0,targetVectorSequence.getLength()):
            for d in range(0,targetVectorSequence.getDimensionality()):
                diff = (targetVectorSequence.getFeatureVector(t).getVector().get(d)-meanVector.get(d))
                varianceVector.set(d,varianceVector.get(d)+diff*diff)

        varianceVector/=targetVectorSequence.getLength()
        vFS=FeatureSequence()
        vFS.setMatrix(varianceVector.toRowMatrix())
        mFS=FeatureSequence()
        mFS.setMatrix(meanVector.toRowMatrix())
        return (mFS, vFS)

def getGlobalVarianceSequenceFromList(fslist):
        totalLength=0
        if(len(fslist)<=0):
            log(logger.Error, "GlobalVariance:: fslist had no entries")
        meanVector=NumericVector(fslist[0].getDimensionality())
        varianceVector=NumericVector(fslist[0].getDimensionality())
        for fs in fslist:
            totalLength+=fs.getLength()
            for t in range(0,fs.getLength()):
                meanVector+=fs.getFeatureVector(t).getVector()

        meanVector/=totalLength

        for fs in fslist:
            for t in range(0,fs.getLength()):
                for d in range(0,fs.getDimensionality()):
                    diff = (fs.getFeatureVector(t).getVector().get(d)-meanVector.get(d))
                    varianceVector.set(d,varianceVector.get(d)+diff*diff)

        varianceVector/=totalLength
        return (meanVector, varianceVector)

def applyGV(fs, gvs):
        (utteranceMean, utteranceVariance)=getGlobalVarianceSequence(fs)
        gvvMean=getGlobalVarianceSequenceFromList(gvs[0])[0] #mean of means
        gvvVariance=getGlobalVarianceSequenceFromList(gvs[1])[0] #mean of variances
        meanV=utteranceMean.getFeatureVector(0).getVector()
        varV=utteranceVariance.getFeatureVector(0).getVector()
        for vectorIndex in range(0,fs.getLength()):
            for dim in range(0,fs.getDimensionality()):
                mSV=fs.getFeatureVector(vectorIndex).getVector()
                sDQ=math.sqrt(gvvVariance.get(dim))/math.sqrt(varV.get(dim))
                #log(logger.Debug,"MSV before:"+str(mSV.get(dim))+" SDQ "+str(sDQ))
                mSV.set(dim,sDQ*(mSV.get(dim)-meanV.get(dim))+meanV.get(dim))
                #log(logger.Debug,"MSV after:"+str(mSV.get(dim))+" Mean "+str(meanV.get(dim)))
        return fs


# -*- coding: utf8 -*-

from . import BioKIT
from .BioKIT import *
from math import *

def correlateFilesWithFilter(xName, yName, whichName):
    """Calculate pearson correlation of two sequences loaded
       from files, leaving out items marked with 0 in which, using
       only data up to the length of the shorter one."""
    with open(xName) as xFile:
        x = xFile.readlines()
    with open(yName) as yFile:
        y = yFile.readlines()
    with open(whichName) as whichFile:
        which = whichFile.readlines()
    return correlateWithFilter([float(v) for v in x], [float(v) for v in y], min(len(x), len(y)), which)
        
def correlateWithFilter(x, y, which, n):
    """Calculate pearson correlation of two sequences of equal length n,
       leaving out items marked with 0 in which"""
    sampleCount = n
    filterSampleCount = 0
    xFilter = []
    yFilter = []
    for i in range(sampleCount):
        if which[i] == 1:
            filterSampleCount += 1
            xFilter.append(x[i])
            yFilter.append(y[i])
    return Correlate(xFilter, yFilter, filterSampleCount)
        
def correlateFiles(xName, yName):
    """Calculate pearson correlation of two sequences of equal length n loaded
       from files, using only data up to the length of the shorter one."""
    with open(xName) as xFile:
        x = xFile.readlines()
    with open(yName) as yFile:
        y = yFile.readlines()
    return correlate([float(v) for v in x], [float(v) for v in y], min(len(x), len(y)))
    
def correlate(x, y, n):
    """Calculate pearson correlation of two sequences of equal length n"""
    sampleCount = n
    
    xSum = 0
    ySum = 0
    for i in range(sampleCount):
        xSum += float(x[i])
        ySum += float(y[i])
    xMean = xSum / float(sampleCount)
    yMean = ySum / float(sampleCount)

    denSum = 0
    xNumSum = 0
    yNumSum = 0
    for i in range(sampleCount):
        denSum += (float(x[i]) - xMean) * (float(y[i]) - yMean)
        xNumSum += (float(x[i]) - xMean) * (float(x[i]) - xMean)
        yNumSum += (float(y[i]) - yMean) * (float(y[i]) - yMean)
    denominator = sqrt(xNumSum * yNumSum)

    if denominator == 0:
        return 0
    else:
        return (denSum / denominator)

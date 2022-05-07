"""
Utility functions to convert numpy to BioKIT data structures and vice versa.
"""

from . import BioKIT
import numpy

def array2mcfs(arr, isbegin = True, isend = True):
    """
    Convert an ndarray to a MultiChannelFeatureSeqeuence.
    
    Each column of the array will result in one FeatureSequence.
    
    Keyword arguments:
    arr - the numpy ndarray
    isbegin - is the begin of a sequence of feature sequences
    isend - is the end of a sequence of feature sequences
    """
    mcfs = []
    for channel in arr.T:
        fs = BioKIT.FeatureSequence()
        fs = BioKIT.FeatureSequence(numpy.atleast_2d(channel).T, isbegin, isend)
        mcfs.append(fs)
    return mcfs


def array2fs(arr):
    """
    Convert a numpy ndarray to a FeatureSequence
    
    Keyword arguments:
    arr - the numpy ndarray
    """
    fs = BioKIT.FeatureSequence()
    fs.setMatrix(arr)
    return fs

def mcfs2array(mcfs):
    """
    Convert a MultiChannelFeatureSequence to a numpy array.
    
    Assumes all feature sequences stored in the MCFS have the same length.
    
    Keyword arguments:
    mcfs - mcfs to convert
    """
    dim1 = mcfs[0].getLength() # assume same length of all FeatureSequences
    dim2 = 0
    for fs in mcfs:
        dim2 += fs.getDimensionality()
    ar = numpy.empty((dim1,dim2))
    counter = 0
    for fs in mcfs:
        fsar = fs.getMatrix()
        ar[:,counter:(counter+fsar.shape[1])] = fsar
        counter += fsar.shape[1]
    return ar

def fs2array(fs):
    """
    Convert a FeatureSequence to a numpy ndarray
    
    Keyword arguments:
    fs - FeatureSequence object
    """
    arr = numpy.array(fs.getMatrix().list())
    return(arr)

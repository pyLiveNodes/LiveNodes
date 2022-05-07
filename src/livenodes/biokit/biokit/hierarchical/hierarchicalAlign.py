# -*- coding: utf8 -*-

import copy
import string
import sys

import BioKIT


def align(reference, hypothesis):
    """
    Calculate word level alignment between reference and hypothesis

    Parameters:
        reference - reference string
        hypothesis - hypothesis string

    Returns:
        A tuple containing
        - the total cost of this alignment where all insertions, deletions and
        substitution are realized as a cost of 1
        - a backpointer table
        - number of reference words
        - number of hypothesis words
        - list of reference words
        - list fo hypothesis words
    """

    # Currently all insertions, deletions and substitution are realized as a cost of 1

    # Backpointer constants
    EQU = 0
    SUB = 1
    INS = 2
    DEL = 3

    splittedTokenSequence = reference.split()
    splittedHypothesis = hypothesis.split()
    referenceLength = len(splittedTokenSequence)
    hypothesisLength = len(splittedHypothesis)

    # --------------------------------------- #
    # initialize full cumulative score matrix #
    # --------------------------------------- #

    cummulativeScores = [[100000 for col in range(0, hypothesisLength + 1)]
                         for row in range(0, referenceLength + 1)]
    bp = [[-1 for col in range(0, hypothesisLength + 1)]
          for row in range(0, referenceLength + 1)]

    cummulativeScores[0][0] = 0
    for refX in range(1, referenceLength + 1):
        cummulativeScores[refX][0] = cummulativeScores[refX - 1][0] + 1
        bp[refX][0] = DEL
    for hyX in range(1, hypothesisLength + 1):
        cummulativeScores[0][hyX] = cummulativeScores[0][hyX - 1] + 1
        bp[0][hyX] = INS

    # ---------------- #
    # do the alignment #
    # ---------------- #
    refX = 1

    for refW in splittedTokenSequence[:]:
        hyX = 1
        for hyW in splittedHypothesis[:]:

            newscore = cummulativeScores[
                refX - 1][hyX] + 1  # try transition 0: insertion
            if newscore < cummulativeScores[refX][hyX]:
                bp[refX][hyX] = DEL
                cummulativeScores[refX][hyX] = newscore

            if splittedTokenSequence[refX - 1] == splittedHypothesis[
                    hyX - 1]:  # try transition 1: substitution
                newscore = cummulativeScores[refX - 1][hyX - 1]
                DIFF = EQU
            else:
                newscore = cummulativeScores[refX - 1][hyX - 1] + 1
                DIFF = SUB
            if newscore < cummulativeScores[refX][hyX]:
                bp[refX][hyX] = DIFF
                cummulativeScores[refX][hyX] = newscore

            newscore = cummulativeScores[refX][
                hyX - 1] + 1  # try transition 2: deletion
            if newscore < cummulativeScores[refX][hyX]:
                bp[refX][hyX] = INS
                cummulativeScores[refX][hyX] = newscore

            hyX = hyX + 1
        refX = refX + 1

    # ------------------------------- #
    # retrieve best cummulative score #
    # ------------------------------- #

    refX = referenceLength
    hyX = hypothesisLength

    return (cummulativeScores[refX][hyX], bp, referenceLength,
            hypothesisLength, splittedTokenSequence, splittedHypothesis)


def tokenErrorRate(reference, hypothesis):
    """ Compute the token error rate """
    errorCount = align(reference, hypothesis)[0]
    referenceCount = len(reference.split())
    if referenceCount > 0:
        tokenErrorRate = (float(errorCount) / referenceCount)
    return tokenErrorRate


def totalTokenErrorRate(resultList, refKey='reference', hypoKey='hypothesis'):
    """
    Compute the total Token Error Rate for a list of results

    Arguments:
    resultList - list of results, one result is a dictionary containing
                    reference and hypothesis
    refKey - result dictionary key identifying the reference (default: reference)
    hypoKey - result dictionary key identifying the hypothesis (default: hypothesis)

    Returns:
        total Token Error Rate
    """

    substitutions = 0
    insertions = 0
    deletions = 0
    words = 0
    for result in resultList:
        tokenErrorInfo = tokenErrorRateInsDelSubCount(result[refKey],
                                                      result[hypoKey])
        insertions += tokenErrorInfo[0][1]
        deletions += tokenErrorInfo[0][2]
        substitutions += tokenErrorInfo[0][3]
        words += len(result[refKey].split())
    #print("total token errors, I: " + str(insertions) + " , D:" + str(deletions) +
    #      " , S:" + str(substitutions) + " , total words: " + str(words))
    avgTER = float(insertions + deletions + substitutions) / words
    return avgTER


def tokenErrorRateInsDelSubCount(reference, hypothesis):
    """
    Calculate the numbers of insertions, deletions and substitutions when
    aligning reference and hypothesis

    Returns:
        A list of lists:
            - counts of matches, insertions, deletions and substitutions
            - inserted words
            - deleted words
            - substituted (reference word, hypothesis word) pairs
    """

    results = align(reference, hypothesis)

    bp = results[1]
    referenceLength = results[2]
    hypothesisLength = results[3]
    splittedTokenSequence = results[4]
    splittedHypothesis = results[5]

    subCount = 0
    insCount = 0
    delCount = 0
    eqCount = 0

    currentField = bp[referenceLength][hypothesisLength]

    i = referenceLength  # counter for horizontal position change in DP matrix
    j = hypothesisLength  # counter for vertical position change in DP matrix

    subList = []
    insList = []
    delList = []

    while currentField != -1:  # start position with value -1

        # Traverse DP matrix from position with edit distance to start position
        # and output numbers and tokens of equals, ins, del and sub
        # Note: reference on horizontal lines, hypothesis on vertical lines

        if currentField == 1:  # in case of sub
            subCount = subCount + 1
            subList1 = [
                splittedTokenSequence[i - 1], splittedHypothesis[j - 1]
            ]
            subList.insert(0,
                           subList1)  # insert to the beginning of the sub list
            currentField = bp[i - 1][j - 1]
            i = i - 1
            j = j - 1
        elif currentField == 2:  # in case of ins
            insCount = insCount + 1
            insList.insert(0, splittedHypothesis[
                j - 1])  # insert to the beginning of the ins list
            currentField = bp[i][j - 1]  # change position
            j = j - 1
        elif currentField == 3:  # in case of del
            delCount = delCount + 1
            delList.insert(0, splittedTokenSequence[
                i - 1])  # insert to the beginning of the del list
            currentField = bp[i - 1][j]
            i = i - 1
        elif currentField == 0:  # in case of equal
            eqCount = eqCount + 1
            currentField = bp[i - 1][j - 1]
            i = i - 1
            j = j - 1

    InsDelSubCount = [
        eqCount, insCount, delCount, subCount
    ]  # list with numbers of equals, insertions, deletions and substitutions
    InsDelSub = [InsDelSubCount, insList, delList,
                 subList]  # list with numbers and tokens

    return InsDelSub  # return list with numbers and tokens


def getAlignment(reference, hypothesis):
    """
    Calculate the word alignment between two sentences

    Parameters:
        reference - the reference string
        hypothesis - the hypothesis string

    Returns:
        A dictionary. For each index in the reference words, this dictionary
        contains a list of tuples (hypothesis word index, match/ins/del/sub)
    """

    results = align(reference, hypothesis)

    bp = results[1]
    referenceLength = results[2]
    hypothesisLength = results[3]

    currentField = bp[referenceLength][hypothesisLength]

    i = referenceLength  # counter for horizontal position change in DP matrix
    j = hypothesisLength  # counter for vertical position change in DP matrix

    import collections
    alignment = collections.defaultdict(list)

    while currentField != -1:  # start position with value -1

        # Traverse DP matrix from position with edit distance to start position
        # and output numbers and tokens of equals, ins, del and sub
        # Note: reference on horizontal lines, hypothesis on vertical lines

        if currentField == 1:  # in case of sub
            alignment[i - 1].insert(0, (j - 1, "sub"))
            currentField = bp[i - 1][j - 1]
            i = i - 1
            j = j - 1
        elif currentField == 2:  # in case of ins
            alignment[i - 1].insert(0, (j - 1, "ins"))
            currentField = bp[i][j - 1]
            j = j - 1
        elif currentField == 3:  # in case of del
            alignment[i - 1].insert(0, (j - 1, "del"))
            currentField = bp[i - 1][j]
            i = i - 1
        elif currentField == 0:  # in case of equal
            alignment[i - 1].insert(0, (j - 1, "match"))
            currentField = bp[i - 1][j - 1]
            i = i - 1
            j = j - 1

    return dict(alignment)


def tokenErrorRateForAlignment(alignment):
    """
    Calculate the token error rate from an alignment

    Parameters:
        alignment - A dictionary. For each index in the reference words, this dictionary
                    contains a list of tuples (hypothesis word index, match/ins/del/sub)

    Returns:
        - The token error rate
        - Counts of ins, del, sub
    """

    reference_len = len(alignment)
    if -1 in alignment:
        reference_len -= 1
    ins_count = 0
    sub_count = 0
    del_count = 0
    equ_count = 0

    # accumulate
    for reference_idx in alignment:
        for hypothesis_idx, match_type in alignment[reference_idx]:
            if match_type == "ins":
                ins_count += 1
            elif match_type == "sub":
                sub_count += 1
            elif match_type == "del":
                del_count += 1
            else:
                equ_count += 1

    # calculate error
    token_error_rate = float(ins_count + sub_count + del_count) / reference_len

    return token_error_rate, equ_count, ins_count, del_count, sub_count


def alignHierarchicalPythonOnly(reference, hypothesis):
    insertionPenalties = dict()
    deletionPenalties = dict()
    substitutionPenalties = dict()

    return alignHierarchicalWithPenaltiesPythonOnly(reference, hypothesis,
                                                    insertionPenalties,
                                                    deletionPenalties,
                                                    substitutionPenalties)


def alignHierarchicalWithPenaltiesPythonOnly(reference, hypothesis,
                                             insertionPenalties,
                                             deletionPenalties,
                                             substitutionPenalties):
    """
    Assumes { } to be the grouping of substreams and
    assumes | to be the division between different substreams
    i.e. { a | b } D { e | f }
    is a   e
        D
        b   f
    The Alignment is done on the projection of the reference and the hypothesis on their finest streams
    All finest streams are currently weighted equally independent of the stream topology
    If two tokens in different streams have the same name,
    the substitution of one through the other does not give an error
    """

    print("Entering align.alignHierarchicalWithPenalties")

    penalties = []
    penalties.append(insertionPenalties)
    penalties.append(deletionPenalties)
    penalties.append(substitutionPenalties)

    # Create DTW Matrix

    # Divide reference into finestStreams
    splittedReference = reference.split()

    # Retrieve hierarchy of streams, assumes that hierarchy is the same for reference and hypothesis
    # TODO check whether hierarchies for reference and hypothesis are equal, do we want to handle differing hierarchies?
    [
        numberOfStreams, numberOfSubStreams, numberOfFinestStreams,
        firstSubStreamIndex
    ] = retrieveHierarchy(splittedReference)

    finestStreamCount = numberOfFinestStreams[0]
    referenceSubStream = [[] for col in range(finestStreamCount)]
    referenceStreamIndices = [[] for col in range(finestStreamCount)]
    hypoSubStream = [[] for col in range(finestStreamCount)]
    hypoStreamIndices = [[] for col in range(finestStreamCount)]

    retrieveFinestStreamRepresentation(0, firstSubStreamIndex,
                                       splittedReference, referenceSubStream,
                                       referenceStreamIndices,
                                       numberOfSubStreams,
                                       numberOfFinestStreams)

    for i in range(len(referenceSubStream)):
        referenceSubStream[i].insert(
            0, ' '
        )  #This is done to enable the dtw calculation to delete or substitute the first value
        print(referenceSubStream[i])

    #Divide hypo into finestStreams
    splittedHypo = hypothesis.split()
    #Changes hypoSubStream and hypoStreamIndices
    retrieveFinestStreamRepresentation(0, firstSubStreamIndex, splittedHypo,
                                       hypoSubStream, hypoStreamIndices,
                                       numberOfSubStreams,
                                       numberOfFinestStreams)

    for i in range(len(hypoSubStream)):
        hypoSubStream[i].insert(
            0, ' '
        )  #This is done to enable the dtw calculation to insert or substitute the first value
        print(hypoSubStream[i])

    #TODO:   Start here! Needed params:
    #        -vector<vector<String> >  referenceSubStream
    #        -vector<vector<String> >  hypoSubStream
    #        -int                numberOfSubStreams
    #        -int                numberOfFinestStreams
    #        -vector<int>        firstSubStreamIndex
    #        -vector<String>     splittedHypo
    #        -vector<String>     splittedReference

    #Initialize cummulative scores
    #Create dtw matrix for hypothesis only
    lastSubSpace = []

    #Initialize backpointer table with [0,0,0,...,0] for each field
    backPointerTemplate = []
    for dimension in range(len(referenceSubStream) + len(hypoSubStream)):
        backPointerTemplate.append(0)
    entry = [sys.maxsize,
             backPointerTemplate]  #initial score, initial back pointer
    lastSubSpace = initializeCummulativeScores(lastSubSpace, hypoSubStream, 0,
                                               entry)

    #Create dtw matrix for reference and add hypo dtw matrix to each field in the reference dtw matrix
    cummulativeScores = []

    cummulativeScores = initializeCummulativeScores(cummulativeScores,
                                                    referenceSubStream, 0,
                                                    lastSubSpace)

    #Create masks for tokens which span more than one finest stream to mask invalid fields in the dtw matrix
    currentPositions = [0 for col in range(len(referenceSubStream))]

    [referenceMasks, referenceMasksIndices, currentPositions
     ] = createMaskForFieldsRecursive(0, firstSubStreamIndex,
                                      splittedReference, referenceSubStream,
                                      currentPositions, numberOfSubStreams,
                                      numberOfFinestStreams)

    currentPositions = [0 for col in range(len(referenceSubStream))]

    [hypoMasks, hypoMasksIndices, currentPositions
     ] = createMaskForFieldsRecursive(0, firstSubStreamIndex, splittedHypo,
                                      hypoSubStream, currentPositions,
                                      numberOfSubStreams,
                                      numberOfFinestStreams)

    tokenSequences = referenceSubStream[:]
    tokenSequences.extend(hypoSubStream)

    #Apply masks to cummulative score matrix
    for index in range(len(referenceMasks)):
        mask = referenceMasks[index]
        maskIndices = referenceMasksIndices[index]

        cummulativeScores = maskCummulativeScoresMatrixRecursive(
            cummulativeScores[:], tokenSequences, mask, maskIndices, 0, 0)

    for index in range(len(hypoMasks)):
        mask = hypoMasks[index]
        maskIndices = hypoMasksIndices[index]

        cummulativeScores = maskCummulativeScoresMatrixRecursive(
            cummulativeScores[:], tokenSequences, mask, maskIndices, 0,
            len(referenceSubStream))

    #Calculate DTW Scores
    cummulativeScores = initializeFirstFieldRecursive(cummulativeScores[:], 0,
                                                      len(tokenSequences))

    #TODO store backpointers for each field

    print("align searching best match")
    withPenalties = False
    if (len(penalties[0]) > 0):
        withPenalties = True
    if (len(penalties[1]) > 0):
        withPenalties = True
    if (len(penalties[2]) > 0):
        withPenalties = True
    cummulativeScores = iterateOverFieldsRecursive(cummulativeScores[:], 0,
                                                   len(tokenSequences), [],
                                                   cummulativeScores[:],
                                                   tokenSequences, penalties,
                                                   withPenalties)

    result = retrieveFinalScore(cummulativeScores[:], 0, len(tokenSequences))

    #    print 'cummulativeScores', cummulativeScores

    #Find best path through DTW matrix

    finalError = result / (
        finestStreamCount * 1.0
    )  #TODO This is due to the fact, that we do not use the partial scores for the finest stream yet

    #TODO Calculate Insertions, Deletions and Substitutions based on backPointer table, and finestStreamRepresentations
    #Initialize substitution, deletion and insertion count for each stream
    #Set CurrentIndices to final field
    #Prepare error variables for each stream

    print("align backtracing and collecting errors")

    currentPositions = []
    substitutions = []
    insertions = []
    deletions = []
    for index in range(len(referenceSubStream)):
        currentPositions.append(len(referenceSubStream[index]) - 1)
    for streamIndex in range(numberOfStreams):
        substitutions.append([])
        insertions.append([])
        deletions.append([])
        for destStreamIndex in range(numberOfStreams):
            substitutions[streamIndex].append([])
            for index in range(len(referenceSubStream)):
                substitutions[streamIndex][destStreamIndex].append(dict())
        for index in range(len(referenceSubStream)):
            insertions[streamIndex].append(dict())
            deletions[streamIndex].append(dict())
    for index in range(len(hypoSubStream)):
        currentPositions.append(len(hypoSubStream[index]) - 1)
    currentBackPointer = retrievePositionValue(cummulativeScores, 0,
                                               len(tokenSequences),
                                               currentPositions)[1]
    #Prepare error count variables for each finest stream
    insCount = [0 for stream in range(len(referenceSubStream))]
    subCount = [0 for stream in range(len(referenceSubStream))]
    delCount = [0 for stream in range(len(referenceSubStream))]
    offset = len(currentPositions) / 2
    alignedReferenceAtFinestStream = []
    alignedHypoAtFinestStream = []

    for dimension in range(offset):
        alignedReferenceAtFinestStream.append([])
        alignedHypoAtFinestStream.append([])

    #while not in first field
    while (inFirstField(currentPositions) == False):

        #        print 'CurrentPosition is: ', currentPositions
        #        print 'BackPointer is: ', currentBackPointer
        #for all dimensions
        backTraced = False
        for dimension in range(offset):
            #if substitution
            currentReferenceToken = referenceSubStream[dimension][
                currentPositions[dimension]]
            currentHypoToken = hypoSubStream[dimension][currentPositions[
                dimension + offset]]
            if ((currentBackPointer[dimension] == -1) &
                (currentBackPointer[dimension + offset] == -1)):
                backTraced = True
                maxLength = len(currentReferenceToken)
                if (len(currentHypoToken) > maxLength):
                    maxLength = len(currentHypoToken)
                if (currentReferenceToken != currentHypoToken):
                    subCount[dimension] = subCount[dimension] + 1
                    fromStream = referenceStreamIndices[dimension][
                        currentPositions[dimension] -
                        1]  # referenceStream has a leading ' '
                    toStream = hypoStreamIndices[dimension][
                        currentPositions[dimension + offset] -
                        1]  # hypoStream has a leading ' '
                    substitutions[fromStream][toStream][
                        dimension] = storeSubstitution(
                            substitutions[fromStream][toStream][dimension],
                            currentReferenceToken, currentHypoToken)
                    alignedReferenceAtFinestStream[dimension].insert(
                        0,
                        string.ljust(currentReferenceToken.upper(), maxLength))
                    alignedHypoAtFinestStream[dimension].insert(
                        0, string.ljust(currentHypoToken.upper(), maxLength))
                else:
                    alignedReferenceAtFinestStream[dimension].insert(
                        0, string.ljust(currentReferenceToken, maxLength))
                    alignedHypoAtFinestStream[dimension].insert(
                        0, string.ljust(currentHypoToken, maxLength))

            #elif deletion
            elif ((currentBackPointer[dimension] == -1) &
                  (currentBackPointer[dimension + offset] == 0)):
                backTraced = True
                delCount[dimension] = delCount[dimension] + 1
                streamIndex = referenceStreamIndices[dimension][
                    currentPositions[dimension] -
                    1]  # referenceStream has a leading ' '
                deletions[streamIndex][dimension] = storeInsertionDeletion(
                    deletions[streamIndex][dimension], currentReferenceToken)
                alignedReferenceAtFinestStream[dimension].insert(
                    0, currentReferenceToken.upper())
                dummyHypoToken = ''
                for index in range(len(currentReferenceToken)):
                    list = []
                    list.append(dummyHypoToken)
                    list.append('*')
                    dummyHypoToken = string.join(list, '')
                alignedHypoAtFinestStream[dimension].insert(0, dummyHypoToken)

            #elif insertion
            elif ((currentBackPointer[dimension] == 0) &
                  (currentBackPointer[dimension + offset] == -1)):
                backTraced = True
                insCount[dimension] = insCount[dimension] + 1
                streamIndex = hypoStreamIndices[dimension][
                    currentPositions[dimension + offset] -
                    1]  # hypoStream has a leading ' '
                insertions[streamIndex][dimension] = storeInsertionDeletion(
                    insertions[streamIndex][dimension], currentHypoToken)
                dummyReferenceToken = ''
                for index in range(len(currentHypoToken)):
                    list = []
                    list.append(dummyReferenceToken)
                    list.append('*')
                    dummyReferenceToken = string.join(list, '')
                alignedReferenceAtFinestStream[dimension].insert(
                    0, dummyReferenceToken)
                alignedHypoAtFinestStream[dimension].insert(
                    0, currentHypoToken.upper())

            #else Could not backtrace
            currentPositions[dimension] = currentPositions[
                dimension] + currentBackPointer[dimension]
            currentPositions[dimension + offset] = currentPositions[
                dimension + offset] + currentBackPointer[dimension + offset]

        if (backTraced == False):
            print('Could not backtrace at position ', currentPositions)
        currentBackPointer = retrievePositionValue(cummulativeScores, 0,
                                                   len(tokenSequences),
                                                   currentPositions)[1]
    insDelSubCounts = [insCount, delCount, subCount]
    alignedSequences = [
        alignedReferenceAtFinestStream, alignedHypoAtFinestStream
    ]
    insDelSubErrors = [insertions, deletions, substitutions]
    print('leaving alignHierarchical')

    #TODO:    End here!

    return [
        finalError, referenceSubStream, hypoSubStream, alignedSequences,
        insDelSubCounts, insDelSubErrors
    ]


def alignHierarchical(reference, hypothesis):

    #Create DTW Matrix

    #Divide reference into finestStreams
    splittedReference = reference.split()

    #Retrieve hierarchy of streams, assumes that hierarchy is the same for reference and hypothesis
    #TODO check whether hierarchies for reference and hypothesis are equal, do we want to handle differing hierarchies?
    [
        numberOfStreams, numberOfSubStreams, numberOfFinestStreams,
        firstSubStreamIndex
    ] = retrieveHierarchy(splittedReference)

    finestStreamCount = numberOfFinestStreams[0]
    referenceSubStream = [[] for col in range(finestStreamCount)]
    referenceStreamIndices = [[] for col in range(finestStreamCount)]
    hypoSubStream = [[] for col in range(finestStreamCount)]
    hypoStreamIndices = [[] for col in range(finestStreamCount)]

    retrieveFinestStreamRepresentation(0, firstSubStreamIndex,
                                       splittedReference, referenceSubStream,
                                       referenceStreamIndices,
                                       numberOfSubStreams,
                                       numberOfFinestStreams)

    for i in range(len(referenceSubStream)):
        referenceSubStream[i].insert(
            0, ' '
        )  #This is done to enable the dtw calculation to delete or substitute the first value
        print(referenceSubStream[i])

    #Divide hypo into finestStreams
    splittedHypo = hypothesis.split()
    retrieveFinestStreamRepresentation(0, firstSubStreamIndex, splittedHypo,
                                       hypoSubStream, hypoStreamIndices,
                                       numberOfSubStreams,
                                       numberOfFinestStreams)

    for i in range(len(hypoSubStream)):
        hypoSubStream[i].insert(
            0, ' '
        )  #This is done to enable the dtw calculation to insert or substitute the first value
        print(hypoSubStream[i])

    aligner = BioKIT.HierarchicalAlign(referenceSubStream, hypoSubStream,
                                       numberOfStreams, numberOfSubStreams,
                                       numberOfFinestStreams,
                                       firstSubStreamIndex, splittedHypo,
                                       referenceStreamIndices,
                                       hypoStreamIndices, splittedReference)
    aligner.workout()

    alignedSequences = [
        aligner.getAlignedReferenceAtFinestStream(),
        aligner.getAlignedHypoAtFinestStream()
    ]
    insDelSubCounts = [
        aligner.getInsCount(),
        aligner.getDelCount(),
        aligner.getSubCount()
    ]
    insDelSubErrors = [
        aligner.getInsertions(),
        aligner.getDeletions(),
        aligner.getSubstitutions()
    ]

    return [
        aligner.getFinalError(), referenceSubStream, hypoSubStream,
        alignedSequences, insDelSubCounts, insDelSubErrors
    ]


#def calculeFScore(insDelSubCounts):
#    refCount = []
#    hypoCount = []
#    correctCount = []
#    allTokens = []
#    for dimension in range(len(alignedReferenceSequences)):
#        refCount.append(dict())
#        hypoCount.append(dict())
#        correctCount.append(dict())
#        allTokens.append(dict())
#        for index in range(len(alignedReferenceSequences[dimension])):
#            if (alignedReferenceSequences[dimension][index] == alignedHypoSequences[dimension][index]):
#                #increase all counts
#                refCount[dimension] = increaseCount(refCount[dimension], alignedReferenceSequences[dimension][index])
#                hypoCount[dimension] = increaseCount(hypoCount[dimension], alignedHypoSequences[dimension][index])
#                correctCount[dimension] = increaseCount(correctCount[dimension], alignedReferenceSequences[dimension][index])
#                allTokens[dimension] = increaseCount(allTokens[dimension], alignedReferenceSequences[dimension][index])
#            else:
#                if (string.find(alignedReferenceSequences[dimension][index], '*') == -1):
#                    #increase refCount
#                    refCount[dimension] = increaseCount(refCount[dimension], alignedReferenceSequences[dimension][index])
#                    allTokens[dimension] = increaseCount(allTokens[dimension], alignedReferenceSequences[dimension][index])
#                if (string.find(alignedHypoSequences[dimension][index], '*') == -1):
#                    #increase hypoCount
#                    hypoCount[dimension] = increaseCount(hypoCount[dimension], alignedHypoSequences[dimension][index])
#                    allTokens[dimension] = increaseCount(allTokens[dimension], alignedReferenceSequences[dimension][index])
#        for token in


def storeSubstitution(substitutions, currentReferenceToken, currentHypoToken):
    if (not currentReferenceToken in substitutions):
        substitutions[currentReferenceToken] = dict()
    if (not currentHypoToken in substitutions[currentReferenceToken]):
        substitutions[currentReferenceToken][currentHypoToken] = 1
    else:
        substitutions[currentReferenceToken][currentHypoToken] = substitutions[
            currentReferenceToken][currentHypoToken] + 1
    return substitutions


def storeInsertionDeletion(insertionDeletion, currentToken):
    if (not currentToken in insertionDeletion):
        insertionDeletion[currentToken] = 1
    else:
        insertionDeletion[currentToken] = insertionDeletion[currentToken] + 1
    return insertionDeletion


def inFirstField(currentPositions):
    inFirstField = True
    for index in range(len(currentPositions)):
        if (currentPositions[index] != 0):
            inFirstField = False
    return inFirstField


"""
Return token error rate which is calculated as
"alignment errors" / "average length of reference in finest streams"
The calculation is done on the projection of the reference and the hypothesis on their finest streams
All finest streams are currently weighted equally independent of the stream topology
"""


def tokenErrorRateHierarchical(reference, hypothesis):
    insertionPenalties = dict()
    deletionPenalties = dict()
    substitutionPenalties = dict()

    return tokenErrorRateHierarchicalWithPenalties(reference, hypothesis,
                                                   insertionPenalties,
                                                   deletionPenalties,
                                                   substitutionPenalties,
                                                   False)


"""
Return token error rate which is calculated as
"alignment errors" / "average length of reference in finest streams"
The calculation is done on the projection of the reference and the hypothesis on their finest streams
All finest streams are currently weighted equally independent of the stream topology
"""


def tokenErrorRateHierarchicalPythonOnly(reference, hypothesis):
    insertionPenalties = dict()
    deletionPenalties = dict()
    substitutionPenalties = dict()

    return tokenErrorRateHierarchicalWithPenalties(reference, hypothesis,
                                                   insertionPenalties,
                                                   deletionPenalties,
                                                   substitutionPenalties, True)


"""
Return token error rate which is calculated as
"alignment errors" / "average length of reference in finest streams"
The calculation is done on the projection of the reference and the hypothesis on their finest streams
All finest streams are currently weighted equally independent of the stream topology
"""


def tokenErrorRateHierarchicalWithPenalties(reference,
                                            hypothesis,
                                            insertionPenalties,
                                            deletionPenalties,
                                            substitutionPenalties,
                                            usePython=True):

    print("Entering align.tokenErrorRateHierarchicalWithPenalties")

    if (len(insertionPenalties) > 0):
        print(
            "WARN: Can only calculate error rate with penalties if using python method -> Using python method"
        )
        usePython = True
    if (len(deletionPenalties) > 0):
        print(
            "WARN: Can only calculate error rate with penalties if using python method -> Using python method"
        )
        usePython = True
    if (len(substitutionPenalties) > 0):
        print(
            "WARN: Can only calculate error rate with penalties if using python method -> Using python method"
        )
        usePython = True

    if (usePython == True):
        print("Using python implementation of alignHierarchical")
        [
            errorCount, referenceAtFinestStream, hypoAtFinestStream,
            alignedSequences, insDelSubCounts, insDelSubErrors
        ] = alignHierarchicalWithPenaltiesPythonOnly(reference, hypothesis,
                                                     insertionPenalties,
                                                     deletionPenalties,
                                                     substitutionPenalties)
    else:
        print("Using c++ implementation of alignHierarchical")
        [
            errorCount, referenceAtFinestStream, hypoAtFinestStream,
            alignedSequences, insDelSubCounts, insDelSubErrors
        ] = alignHierarchical(reference, hypothesis)

#The reference length is the average over the projections of the reference into the finest streams
    referenceLength = 0.0
    finestStreamCount = len(referenceAtFinestStream)
    for index in range(finestStreamCount):
        for position in range(
                1, len(referenceAtFinestStream[index])
        ):  # We need to skip the 0th entry since we have a leading ' ' for each reference sequence
            if (referenceAtFinestStream[index][position] in deletionPenalties):
                referenceLength += deletionPenalties[
                    referenceAtFinestStream[index][position]]
            else:
                referenceLength += 1
    referenceLength = referenceLength / (finestStreamCount * 1.0)

    offset = len(alignedSequences[0])
    for dimension in range(offset):
        print('Dimension ', dimension)
        print('Aligned Reference : ', alignedSequences[0][dimension])
        print('Aligned Hypothesis: ', alignedSequences[1][dimension])

        for dimension in range(len(insDelSubCounts[2])):
            print('Dimension ', dimension)
            print('  Insertions', insDelSubCounts[0][dimension])
            print('  Deletions', insDelSubCounts[1][dimension])
            print('  Substitutions', insDelSubCounts[2][dimension])

        for fromStream in range(len(insDelSubErrors[2])):
            for toStream in range(len(insDelSubErrors[2][fromStream])):
                print('Stream (from -> to): ', fromStream, ' -> ', toStream)
                for dimension in range(
                        len(insDelSubErrors[2][fromStream][toStream])):
                    print('Dimension: ', dimension)
                    for key in insDelSubErrors[2][fromStream][toStream][
                            dimension]:
                        for value in insDelSubErrors[2][fromStream][toStream][
                                dimension][key]:
                            print(
                                key, '-> ', value, insDelSubErrors[2]
                                [fromStream][toStream][dimension][key][value])

    return [((1.0 * errorCount) / referenceLength), referenceAtFinestStream,
            hypoAtFinestStream, alignedSequences, insDelSubCounts,
            insDelSubErrors]
"""
This method goes through the token sequence in breadth first search and retrieves the hierarchy of the streams.
Param tokenSequence is the token sequence for which the stream hierarchy has to be retrieved
Return numberOfSubStreams Amount of sub streams for each stream
Return numberOfFinestStreams Amount of finest streams belonging to each stream
Return firstSubStreamIndex Index of the first sub stream of each stream
"""


def retrieveHierarchy(tokenSequence):
    maxStreamIndexForHierarchy = 0
    #Contains a list of: the partial token sequence, the stream index and the parent stream indices
    streamParts = [[tokenSequence, 0, []]]
    firstSubStreamIndex = []
    numberOfFinestStreams = []
    numberOfFinestStreams.append(1)
    numberOfSubStreams = []
    while (len(streamParts) > 0):
        newStreamParts = []
        for streamPart in streamParts:
            currentPosition = 0
            #while not at the end of the token sequence
            while (currentPosition < len(streamPart[0])):
                #Retrieve next entry: Either { Foo bar { ... } } or Foo
                #If starts with { find matching }
                newCurrentPosition = currentPosition + 1
                if (streamPart[0][currentPosition] == '{'):
                    bracketCount = 1
                    while ((bracketCount > 0) &
                           (newCurrentPosition < len(streamPart[0]))):
                        if (streamPart[0][newCurrentPosition] == '}'):
                            bracketCount = bracketCount - 1
                        elif (streamPart[0][newCurrentPosition] == '{'):
                            bracketCount = bracketCount + 1
                        newCurrentPosition = newCurrentPosition + 1
                    if (bracketCount == 0):
                        newStreamPart = streamPart[0][currentPosition +
                                                      1:newCurrentPosition - 1]
                    else:
                        print('Error with finding } while parsing', streamPart)

                    #For each subStream retrieve representation in finest SubStreams
                    startIndex = 0
                    endIndex = 0
                    subStreamCount = 0

                    #If we haven't been in this sub streams, we have to initialize some variables
                    retrieveNewValues = False
                    if (len(firstSubStreamIndex) > streamPart[1]):
                        subStreamIndex = firstSubStreamIndex[streamPart[1]]
                    else:
                        retrieveNewValues = True
                        subStreamIndex = maxStreamIndexForHierarchy + 1
                        firstSubStreamIndex.append(subStreamIndex)

                    # divide stream part into sub streams and store partial token sequences for next iteration in breadth first search
                    bracketCount = 0
                    while (endIndex < len(newStreamPart)):
                        if (newStreamPart[endIndex] == '}'):
                            bracketCount = bracketCount - 1
                        elif (newStreamPart[endIndex] == '{'):
                            bracketCount = bracketCount + 1
                        if ((bracketCount == 0) &
                            (newStreamPart[endIndex] == '|')):
                            if (streamPart[2] == []):
                                newStreamParts.append([
                                    newStreamPart[startIndex:endIndex],
                                    subStreamIndex, [streamPart[1]]
                                ])
                            elif (len(streamPart[2]) == 1):
                                newStreamParts.append([
                                    newStreamPart[startIndex:endIndex],
                                    subStreamIndex,
                                    [streamPart[2], streamPart[1]]
                                ])
                            else:
                                newStreamParts.append([
                                    newStreamPart[startIndex:endIndex],
                                    subStreamIndex,
                                    streamPart[2].append(streamPart[1])
                                ])
                            startIndex = endIndex + 1
                            subStreamIndex = subStreamIndex + 1
                            subStreamCount = subStreamCount + 1
                            if (len(numberOfFinestStreams) <= subStreamIndex):
                                numberOfFinestStreams.append(1)

                        endIndex = endIndex + 1

                    if (streamPart[2] == []):
                        newStreamParts.append([
                            newStreamPart[startIndex:], subStreamIndex,
                            [streamPart[1]]
                        ])
                    elif (len(streamPart[2]) == 1):
                        newStreamParts.append([
                            newStreamPart[startIndex:], subStreamIndex,
                            [streamPart[2], streamPart[1]]
                        ])
                    else:
                        newStreamParts.append([
                            newStreamPart[startIndex:], subStreamIndex,
                            streamPart[2].append(streamPart[1])
                        ])

                    subStreamCount = subStreamCount + 1
                    if (len(numberOfFinestStreams) <= subStreamIndex):
                        numberOfFinestStreams.append(1)

                    #If we are in this sub stream for the first time, we need to fill the hierarchy variables
                    if (retrieveNewValues == True):
                        for index in streamPart[2]:
                            numberOfFinestStreams[index] += subStreamCount - 1
                        numberOfFinestStreams[
                            streamPart[1]] += subStreamCount - 1
                        maxStreamIndexForHierarchy = maxStreamIndexForHierarchy + subStreamCount
                        numberOfSubStreams.append(subStreamCount)

                currentPosition = newCurrentPosition
        streamParts = newStreamParts[:]
    return [
        maxStreamIndexForHierarchy + 1, numberOfSubStreams,
        numberOfFinestStreams, firstSubStreamIndex
    ]


#Be careful, we currently modify cummulativeScoresPart here through call by reference
def iterateOverFieldsRecursive(cummulativeScoresPart, currentDimension,
                               maxDepth, currentPositions, cummulativeScores,
                               tokenSequences, penalties, withPenalties):
    if (currentDimension < maxDepth):
        for index in range(len(cummulativeScoresPart)):
            currentPositions.append(index)
            cummulativeScoresPart[index] = iterateOverFieldsRecursive(
                cummulativeScoresPart[index], currentDimension + 1, maxDepth,
                currentPositions, cummulativeScores, tokenSequences, penalties,
                withPenalties)
            currentPositions.pop()
    else:
        # Current Field must be valid (cummulative score > -1)
        if (cummulativeScoresPart[0] != -1):
            cummulativeScoresPart = makeTransitionsRecursive(
                cummulativeScores, cummulativeScoresPart[:], [],
                currentPositions, [], [], 0, maxDepth, tokenSequences,
                penalties, withPenalties)


#            print 'New score for ', currentPositions, 'is ', cummulativeScoresPart[0]

    return cummulativeScoresPart


def makeTransitionsRecursive(cummulativeScores, cummulativeScoreValue,
                             sourcePositions, currentPositions,
                             referenceValues, hypoValues, currentDimension,
                             maxDepth, tokenSequence, penalties,
                             withPenalties):
    value = cummulativeScoreValue
    if (currentDimension < maxDepth):
        for index in [-1, 0]:  #Transition or no transition
            #            print "Now appending to sourcePositions: ",
            #            print (currentPositions[currentDimension] + index);
            sourcePositions.append(currentPositions[currentDimension] + index)
            if (
                    currentDimension < len(tokenSequence) / 2
            ):  #TODO Assumes that number of finest streams in reference == number of finest streams in hypo, e.g. check this at the beginning of the align script
                referenceValues.append(tokenSequence[currentDimension][
                    currentPositions[currentDimension]])
            else:
                hypoValues.append(
                    tokenSequence[currentDimension][
                        currentPositions[currentDimension]]
                )  #TODO Assumes that number of finest streams in reference == number of finest streams in hypo, e.g. check this at the beginning of the align script
            value = makeTransitionsRecursive(cummulativeScores, value,
                                             sourcePositions, currentPositions,
                                             referenceValues, hypoValues,
                                             currentDimension + 1, maxDepth,
                                             tokenSequence, penalties,
                                             withPenalties)
            sourcePositions.pop()
            if (
                    currentDimension < len(tokenSequence) / 2
            ):  #TODO Assumes that number of finest streams in reference == number of finest streams in hypo, e.g. check this at the beginning of the align script
                referenceValues.pop()
            else:
                hypoValues.pop()
    else:
        #        print 'Updating score for transition from: ', sourcePositions, ' to ', currentPositions
        #All source positions must be >= 0
        possibleTransition = True
        for index in range(len(sourcePositions)):
            if (sourcePositions[index] < 0):
                possibleTransition = False

        #source positions must differ from currentPositions
        allEqual = True
        for index in range(len(sourcePositions)):
            if (sourcePositions[index] != currentPositions[index]):
                allEqual = False
        if (possibleTransition & (allEqual == False)):
            offset = len(
                sourcePositions
            ) / 2  #TODO Assumes that number of finest streams in reference == number of finest streams in hypo, e.g. check this at the beginning of the align script
            additionalScore = 0
            text = ' '
            backPointer = [0 for index in range(offset + offset)]
            for index in range(offset):
                #Diagonal transition (substitution or equal tokens)
                if ((sourcePositions[index] != currentPositions[index]) &
                    ((sourcePositions[index + offset] !=
                      currentPositions[index + offset]))):
                    #                    print 'Performing diagonal transition from: ', sourcePositions, ' to ', currentPositions
                    #                    text = text, 'Performing diagonal transition from: ', sourcePositions, ' to ', currentPositions
                    backPointer[index] = -1
                    backPointer[index + offset] = -1
                    if (referenceValues[index] !=
                            hypoValues[index]):  #substitution
                        substitutionValue = referenceValues[
                            index] + "," + hypoValues[index]
                        if (withPenalties and substitutionValue in penalties[2]
                            ):  #substitionPenalties have been specified
                            additionalScore = additionalScore + penalties[2][
                                substitutionValue]
                        #Use maximum of insertion and deletion penalty to simulate substitution score, default is 1
                        elif (withPenalties
                              and referenceValues[index] in penalties[1]
                              or hypoValues[index] in penalties[0]):
                            maxScore = 0
                            if (referenceValues[index] in penalties[1]):
                                maxScore = penalties[1][referenceValues[index]]
                            else:
                                maxScore = 1
                            if (hypoValues[index] in penalties[0]):
                                if (penalties[0][hypoValues[index]] >
                                        maxScore):
                                    maxScore = penalties[0][hypoValues[index]]
                            else:
                                if (maxScore < 1):
                                    maxScore = 1
                            additionalScore = additionalScore + maxScore
                        else:
                            additionalScore = additionalScore + 1  #TODO Need to use the partial score for this stream
                elif (sourcePositions[index] !=
                      currentPositions[index]):  #deletion
                    #                    print 'Performing deletion from: ', sourcePositions, ' to ', currentPositions
                    #                    text = text, 'Performing deletion from: ', sourcePositions, ' to ', currentPositions
                    backPointer[index] = -1
                    if (withPenalties
                            and referenceValues[index] in penalties[1]):
                        additionalScore = additionalScore + penalties[1][
                            referenceValues[index]]
                    else:
                        additionalScore = additionalScore + 1  #TODO Need to use the partial score for this stream
                elif (sourcePositions[index + offset] !=
                      currentPositions[index + offset]):  #insertion
                    #                    print 'Performing insertion from: ', sourcePositions, ' to ', currentPositions
                    #                    text = text, 'Performing insertion from: ', sourcePositions, ' to ', currentPositions
                    backPointer[index + offset] = -1
                    if (withPenalties and hypoValues[index] in penalties[0]):
                        additionalScore = additionalScore + penalties[0][
                            hypoValues[index]]
                    else:
                        additionalScore = additionalScore + 1  # TODO Need to use the partial score for this stream
            #if cummulativeScores at source position + additionalScore < cummulativeScores at current position than replace the cummulative score at the current position
            sourceValue = retrievePositionValue(cummulativeScores, 0, maxDepth,
                                                sourcePositions)[0]
            if ((sourceValue != -1) &
                ((sourceValue + additionalScore) < value[0])):
                #                print text
                #                print 'Old score is: ',value[0], ' new score is: ', (sourceValue + additionalScore)
                #                print 'backPointer is: ', backPointer
                value = [(sourceValue + additionalScore), backPointer[:]]

    return value


"""
Return the value for a given position in the cummulative scores matrix
"""


def retrievePositionValue(cummulativeScoresPart, currentDimension, maxDepth,
                          positions):
    newCummulativeScoresPart = cummulativeScoresPart
    if (currentDimension < maxDepth):
        #print 'currentDimension ', currentDimension
        #print 'positions[cD]', positions[currentDimension]
        value = retrievePositionValue(
            newCummulativeScoresPart[positions[currentDimension]][:],
            currentDimension + 1, maxDepth, positions)
        return value
    else:
        return newCummulativeScoresPart


"""
Return value of the first field in the cummulative scores matrix
"""


def initializeFirstFieldRecursive(cummulativeScores, currentDimension,
                                  maxDepth):
    if (currentDimension < maxDepth):
        cummulativeScores[0] = initializeFirstFieldRecursive(
            cummulativeScores[0][:], currentDimension + 1, maxDepth)
        return cummulativeScores
    else:
        return [0, -1]


"""
Return value of the last field in the cummulative scores matrix
"""


def retrieveFinalScore(cummulativeScores, currentDimension, maxDepth):
    newCummulativeScores = cummulativeScores
    if (currentDimension < maxDepth):
        result = retrieveFinalScore(
            newCummulativeScores[len(newCummulativeScores) - 1][:],
            currentDimension + 1, maxDepth)
        return result
    else:
        return newCummulativeScores[
            0]  #First entry is score, second is backpointer


"""
Applies a set of masks to the cummulative scores matrix to invalidate fields that are not possible due to token that span more than one dimension
"""


def maskCummulativeScoresMatrixRecursive(cummulativeScoresPart, tokenSequences,
                                         mask, maskIndices, currentDimension,
                                         offset):
    newCummulativeScoresPart = cummulativeScoresPart
    if (currentDimension == len(tokenSequences)):
        if (mask == 1):
            return [-1, -1]
        else:
            return newCummulativeScoresPart
    elif ((currentDimension >= (maskIndices[0] + offset)) &
          (currentDimension <= (maskIndices[len(maskIndices) - 1] + offset))):
        for index in range(len(mask)):
            subMask = mask[index]
            newCummulativeScoresPart[
                index] = maskCummulativeScoresMatrixRecursive(
                    newCummulativeScoresPart[index][:], tokenSequences,
                    subMask, maskIndices, currentDimension + 1, offset)
    else:
        for index in range(len(tokenSequences[currentDimension])):
            newCummulativeScoresPart[
                index] = maskCummulativeScoresMatrixRecursive(
                    newCummulativeScoresPart[index][:], tokenSequences, mask,
                    maskIndices, currentDimension + 1, offset)

    return newCummulativeScoresPart


"""
This method splits a token sequence into token sequences for the finest sub streams
Param currentStream is the index of the stream that has to be divided into sub streams
Param firstSubStreamIndex is the index in the input list of the first sub stream
Param splittedTokenSequence is the token sequence that has to be divided in to sub streams (as a list)
Param tokenSubStream is the output of this method, i.e. the reference divided into the finest sub streams
Param numberOfSubStreams is a list with the amount of sub streams for each stream
Param numberOfFinestStreams is a list with the amount of finest sub streams for each stream
"""


#TODO In this method tokenSubStream is passed by reference, change to pass by value
def retrieveFinestStreamRepresentation(currentStream, firstSubStreamIndex,
                                       splittedTokenSequence, tokenSubStream,
                                       tokenStreamIndices, numberOfSubStreams,
                                       numberOfFinestStreams):
    currentPosition = 0
    #while not at the end of the reference
    while (currentPosition < len(splittedTokenSequence)):
        #Retrieve next entry: Either { Foo bar { ... } } or Foo
        #If starts with { find matching }
        newCurrentPosition = currentPosition + 1
        if (splittedTokenSequence[currentPosition] == '{'):
            bracketCount = 1
            while ((bracketCount > 0) &
                   (newCurrentPosition < len(splittedTokenSequence))):
                if (splittedTokenSequence[newCurrentPosition] == '}'):
                    bracketCount = bracketCount - 1
                elif (splittedTokenSequence[newCurrentPosition] == '{'):
                    bracketCount = bracketCount + 1
                newCurrentPosition = newCurrentPosition + 1
            if (bracketCount == 0):
                streamPart = splittedTokenSequence[currentPosition +
                                                   1:newCurrentPosition - 1]
            else:
                print('Error with finding } while parsing',
                      splittedTokenSequence)

            #For each subStream retrieve finest SubStream representation
            startIndex = 0
            endIndex = 0
            streamIndex = firstSubStreamIndex[currentStream]

            # divide stream part into sub streams
            bracketCount = 0
            while (endIndex < len(streamPart)):
                if (streamPart[endIndex] == '}'):
                    bracketCount = bracketCount - 1
                elif (streamPart[endIndex] == '{'):
                    bracketCount = bracketCount + 1
                if ((bracketCount == 0) & (streamPart[endIndex] == '|')):
                    retrieveFinestStreamRepresentation(
                        streamIndex, firstSubStreamIndex,
                        streamPart[startIndex:endIndex], tokenSubStream,
                        tokenStreamIndices, numberOfSubStreams,
                        numberOfFinestStreams)
                    startIndex = endIndex + 1
                    streamIndex = streamIndex + 1

                endIndex = endIndex + 1
            retrieveFinestStreamRepresentation(
                streamIndex, firstSubStreamIndex, streamPart[startIndex:],
                tokenSubStream, tokenStreamIndices, numberOfSubStreams,
                numberOfFinestStreams)

        #else get first item and divide item into numberOfFinestStreams streams
        else:
            streamPart = splittedTokenSequence[currentPosition]

            #Retrieve index in finest stream layer
            streamIndex = retrieveFirstIndexOfFinestStream(
                currentStream, firstSubStreamIndex)
            for stream in range(numberOfFinestStreams[currentStream]):
                tokenSubStream[streamIndex].append(streamPart)
                tokenStreamIndices[streamIndex].append(currentStream)
                streamIndex = streamIndex + 1
        currentPosition = newCurrentPosition
    return


"""
Return the finest stream index for this a given stream
"""


def retrieveFirstIndexOfFinestStream(finestStreamIndex, firstSubStreamIndex):
    while (len(firstSubStreamIndex) > finestStreamIndex):
        finestStreamIndex = firstSubStreamIndex[finestStreamIndex]
    firstFinestStreamIndex = 0
    while (len(firstSubStreamIndex) > firstFinestStreamIndex):
        firstFinestStreamIndex = firstSubStreamIndex[firstFinestStreamIndex]
    #Normalize the stream indices to start with 0
    streamIndex = finestStreamIndex - firstFinestStreamIndex
    return streamIndex


"""
This method creates masks for all tokens which span more than one of the finest streams to mask the impossible fields in the dtw matrix
Param currentStream is the stream that has to be divided into sub stream
Param firstSubStreamIndex is the index in the input list of the first sub stream
Param firstIndexOfFinestStream is the first index of the finest stream belonging to this stream
Param splittedTokenSequence is the token sequence that has to be divided in to sub streams (as a list)
Param tokenSubStream represents the token sequence separated into the finest streams
Param currentPositions contains an index for each dimension with the current position in the tokenSubStream
Param numberOfSubStreams is a list with the amount of sub streams for each stream
Param numberOfFinestStreams is a list with the amount of finest sub streams for each stream

Consider the sequence { a | b } G { d f | e } C
The mask will look like (where x are impossible fields):
C x x x x
e   x     x
G x   x x x
b   x     x
  a G d f C
"""


def createMaskForFieldsRecursive(currentStream, firstSubStreamIndex,
                                 splittedTokenSequence, tokenSubStream,
                                 currentPositions, numberOfSubStreams,
                                 numberOfFinestStreams):
    currentPosition = 0

    newMasks = []
    newMasksIndices = []
    #print "call to createMaskForFieldsRecursive with currentPositions: ", currentPositions;
    #print "                                 and splittedTokenSequence: ", splittedTokenSequence
    #print "numberOfFinestStreams: ", numberOfFinestStreams;
    #print "        currentStream: ", currentStream;
    #while not at the end of the reference

    while (currentPosition < len(splittedTokenSequence)):
        #print "Taking while-loop"
        #Retrieve next entry: Either { Foo bar { ... } } or Foo
        #If starts with { find matching }
        newCurrentPosition = currentPosition + 1
        if (splittedTokenSequence[currentPosition] == '{'):
            bracketCount = 1
            while ((bracketCount > 0) &
                   (newCurrentPosition < len(splittedTokenSequence))):
                if (splittedTokenSequence[newCurrentPosition] == '}'):
                    bracketCount = bracketCount - 1
                elif (splittedTokenSequence[newCurrentPosition] == '{'):
                    bracketCount = bracketCount + 1
                newCurrentPosition = newCurrentPosition + 1
            if (bracketCount == 0):
                streamPart = splittedTokenSequence[currentPosition +
                                                   1:newCurrentPosition - 1]
            else:
                print('Error with finding } while parsing',
                      splittedTokenSequence)

            #For each subStream retrieve finest SubStream representation
            startIndex = 0
            endIndex = 0
            streamIndex = firstSubStreamIndex[currentStream]
            scoreMatrixIndex = 0

            # divide stream part into sub streams
            bracketCount = 0
            while (endIndex < len(streamPart)):
                if (streamPart[endIndex] == '}'):
                    bracketCount = bracketCount - 1
                elif (streamPart[endIndex] == '{'):
                    bracketCount = bracketCount + 1
                if ((bracketCount == 0) & (streamPart[endIndex] == '|')):
                    #print "Performing recursive call due to found '|'"
                    #print "    Therefore slicing ", streamPart, " from ", str(startIndex), " to ", str(endIndex), ".";
                    [tempNewMasks, tempNewMasksIndices,
                     currentPositions] = createMaskForFieldsRecursive(
                         streamIndex, firstSubStreamIndex,
                         streamPart[startIndex:endIndex], tokenSubStream,
                         currentPositions, numberOfSubStreams,
                         numberOfFinestStreams)

                    if (tempNewMasks != []):
                        newMasks.extend(tempNewMasks)
                        newMasksIndices.extend(tempNewMasksIndices)

                    startIndex = endIndex + 1
                    streamIndex = streamIndex + 1

                endIndex = endIndex + 1
            #print "Performing recursive call due to end of while-loop."
            #print "    Therefore slicing ", streamPart, " from ", str(startIndex), " to its end."
            [tempNewMasks, tempNewMasksIndices,
             currentPositions] = createMaskForFieldsRecursive(
                 streamIndex, firstSubStreamIndex, streamPart[startIndex:],
                 tokenSubStream, currentPositions, numberOfSubStreams,
                 numberOfFinestStreams)

            if (tempNewMasks != []):
                newMasks.extend(tempNewMasks)
                newMasksIndices.extend(tempNewMasksIndices)

        #else get first item and divide item into numberOfFinestStreams streams
        else:
            #print "currentPositions: ", currentPositions;
            streamPart = splittedTokenSequence[currentPosition]
            streamIndex = retrieveFirstIndexOfFinestStream(
                currentStream, firstSubStreamIndex)
            #print "streamIndex: ", streamIndex
            #This field can be combined with all others
            #print "numberOfFinestStreams: ", numberOfFinestStreams;
            #print "        currentStream: ", currentStream;
            if (numberOfFinestStreams[currentStream] > 1):
                #print "In if case because nrOfFinestStreams[curStream]=",
                #print str(numberOfFinestStreams[currentStream]);
                #print "currentPositions: ", currentPositions
                #Create list with length of the token sequence in the relevant dimensions
                lengths = []
                maskCurrentPositions = []
                newMaskIndices = []
                for stream in range(numberOfFinestStreams[currentStream]):
                    lengths.append(len(tokenSubStream[streamIndex]))
                    newMaskIndices.append(streamIndex)
                    #+ 1 is due to the fact that the masks are created without an empty token at the beginning of the sequences but for the dtw calculation we need such
                    maskCurrentPositions.append(currentPositions[streamIndex] +
                                                1)
                    currentPositions[
                        streamIndex] = currentPositions[streamIndex] + 1
                    streamIndex = streamIndex + 1

                [newMask, dummy] = createMaskRecursive([], lengths, 0, [],
                                                       maskCurrentPositions)
                #print "Return of createMaskRecursive: ", newMask;

                if (newMask != []):
                    newMasks.append(newMask)
                    newMasksIndices.append(newMaskIndices)
            else:
                currentPositions[
                    streamIndex] = currentPositions[streamIndex] + 1

        currentPosition = newCurrentPosition

    #print "returning with currentPositions: ", currentPositions
    return [newMasks, newMasksIndices, currentPositions]


"""
This method actually creates the mask for given fields
"""


def createMaskRecursive(mask, sequenceLengths, currentDim, currentPositions,
                        maskCurrentPositions):
    #print "createMaskRecursive called with mask: ", mask;
    #print "                      sequencLenghts: ", sequenceLengths;
    #print "                          currentDim: ", currentDim;
    #print "                    currentPositions: ", currentPositions;
    #print "                maskCurrentPositions: ", maskCurrentPositions;
    if (currentDim < len(sequenceLengths)):
        mask = [[] for col in range(sequenceLengths[currentDim])]
        for index in range(sequenceLengths[currentDim]):
            currentPositions.append(index)
            [mask[index], currentPositions
             ] = createMaskRecursive(mask, sequenceLengths, currentDim + 1,
                                     currentPositions, maskCurrentPositions)
            currentPositions.pop()
        return [mask, currentPositions]
    else:
        #If at least one currentPosition is equal the maskCurrentPositions and at least one is not equal, the field has to be masked
        notEqualFound = False
        equalFound = False
        for position in range(len(currentPositions)):
            if (currentPositions[position] != maskCurrentPositions[position]):
                notEqualFound = True
            if (currentPositions[position] == maskCurrentPositions[position]):
                equalFound = True
        if (notEqualFound == True & equalFound == True):
            return [1, currentPositions]
        else:
            return [0, currentPositions]


"""
Creates the cummulative scores matrix and initializes each field with a given value/object
"""


def initializeCummulativeScores(cummulativeScoresPart, tokenSequences,
                                currentDimension, lastSubSpace):
    if (currentDimension == len(tokenSequences)):
        return copy.deepcopy(lastSubSpace)
    else:
        cummulativeScoresPart = [
            [] for col in range(len(tokenSequences[currentDimension]))
        ]
        for subSpace in range(len(tokenSequences[currentDimension])):
            currentDimension = currentDimension + 1
            cummulativeScoresPart[subSpace] = initializeCummulativeScores(
                cummulativeScoresPart[subSpace][:], tokenSequences,
                currentDimension, lastSubSpace)
            currentDimension = currentDimension - 1
    return cummulativeScoresPart


def combineAction(primitiveSequence, action):

    print("Entering align.combineAction for action " + action)

    result = ""

    splittedSequence = primitiveSequence.split()

    for primitiveIndex in range(len(splittedSequence) - 1, 1, -1):
        firstPrimitive = splittedSequence[primitiveIndex - 1]
        secondPrimitive = splittedSequence[primitiveIndex]

        if (firstPrimitive.count(action) > 0
                and firstPrimitive == secondPrimitive):
            splittedSequence[primitiveIndex] = ""

    for primitive in splittedSequence:
        if (primitive != ""):
            result += primitive + " "

    result = result.strip()

    return result


def find(minIndex, splittedSequence, sub):
    primitiveIndex = minIndex
    while (primitiveIndex < len(splittedSequence) - 1):
        if (splittedSequence[primitiveIndex] == sub):
            return primitiveIndex
        else:
            primitiveIndex += 1
    return -1


"""
Searches for a sequence of { * | * }. It is a hack and does only work for two layers
"""


def findSeparatedPrimitives(startIndex, splittedSequence):
    firstPrimitives = ""
    secondPrimitives = ""

    firstStart = find(startIndex, splittedSequence, '{')
    if (firstStart != -1):
        #Append primitive not belonging to sequence to be combined
        firstSplit = find(firstStart + 1, splittedSequence, '|')
        if (firstSplit != -1):
            for firstIndex in range(firstStart + 1, firstSplit):
                firstPrimitives += splittedSequence[firstIndex] + ' '
            firstEnd = find(firstSplit + 1, splittedSequence, '}')
            if (firstEnd != -1):
                for firstIndex in range(firstSplit + 1, firstEnd):
                    secondPrimitives += splittedSequence[firstIndex] + ' '
                return [
                    firstStart, firstEnd, firstPrimitives, secondPrimitives
                ]
    return [-1, -1, '', '']


"""
This method is a hack and does only work for a hierarchy of wholebody_center -> wholearm_left | wholearm_right
"""


def normalizeSequence(primitiveSequence):
    primitiveIndex = 0
    splittedSequence = primitiveSequence.split()
    normalizedSequence = []
    secondEnd = -1

    # We can only normalize if we have at least { A | B } { C | D } = 10 entries
    while (secondEnd + 1 < len(splittedSequence) - 10):  #
        firstPrimitives = ""
        secondPrimitives = ""
        #find start
        [startIndex, endIndex, tempFirstPrimitives, tempSecondPrimitives
         ] = findSeparatedPrimitives(secondEnd + 1, splittedSequence)
        if (startIndex != -1):
            for index in range(secondEnd + 1, startIndex):
                normalizedSequence.append(splittedSequence[index] + ' ')
            secondEnd = startIndex - 1
            #while we find matching primitives
            while (startIndex == secondEnd + 1):
                firstPrimitives += tempFirstPrimitives + ' '
                secondPrimitives += tempSecondPrimitives + ' '
                secondEnd = endIndex
                [
                    startIndex, endIndex, tempFirstPrimitives,
                    tempSecondPrimitives
                ] = findSeparatedPrimitives(endIndex + 1, splittedSequence)

            #Append mergedSequence to result
            firstPrimitives = firstPrimitives.strip()
            secondPrimitives = secondPrimitives.strip()
            normalizedSequence.append('{ ')
            normalizedSequence.append(firstPrimitives)
            normalizedSequence.append(' | ')
            normalizedSequence.append(secondPrimitives)
            normalizedSequence.append(' } ')

    for index in range(secondEnd + 1, len(splittedSequence)):
        normalizedSequence.append(splittedSequence[index] + ' ')

    result = ''.join(normalizedSequence)

    result = result.strip()

    return result


"""
This method is a hack and does only work for a hierarchy of wholebody_center -> wholearm_left | wholearm_right
"""


def separatePrimitives(primitiveSequence):

    print("Entering align.separatePrimitives")

    result = ""

    for primitive in primitiveSequence.split():

        if (primitive != '{' and primitive != '}' and primitive != '|'):

            #Check if primitive starts with '_'
            splittedPrimitive = primitive.split('_')
            actions = splittedPrimitive[1].split('!')
            dirObjects = splittedPrimitive[4].split('!')
            indirObjects = splittedPrimitive[5].split('!')
            targets = splittedPrimitive[6].split('!')
            positions = splittedPrimitive[7].split('!')
            directions = splittedPrimitive[8].split('!')
            sequenceType = splittedPrimitive[9]

            separatedPrimitive = dict()
            separatedPrimitive['left'] = ""
            separatedPrimitive['right'] = ""

            if (len(dirObjects) > 1):
                for primitiveIndex in range(len(dirObjects)):
                    side = actions[primitiveIndex * 3 + 2]

                    separatedPrimitive[side] += '_' + actions[
                        primitiveIndex *
                        3] + '_' + actions[primitiveIndex * 3 + 1] + '_' + actions[
                            primitiveIndex * 3 + 2] + '_' + dirObjects[
                                primitiveIndex] + '_' + indirObjects[
                                    primitiveIndex] + '_' + targets[
                                        primitiveIndex] + '_' + positions[
                                            primitiveIndex] + '_' + directions[
                                                primitiveIndex] + '_' + sequenceType + '_ '

                result += '{ ' + separatedPrimitive[
                    'left'] + '| ' + separatedPrimitive['right'] + '}'
            else:
                result += primitive
        else:
            result += primitive

        result += ' '

    result = result.strip()

    print("Leaving align.separatePrimitives")

    return result

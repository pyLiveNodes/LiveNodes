# -*- coding: utf8 -*-

import copy
import string
import sys

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

    cummulativeScores = [[100000 for col in range(0, hypothesisLength+1)] for row in range(0, referenceLength+1)]
    bp = [[-1 for col in range(0, hypothesisLength+1)] for row in range(0, referenceLength+1)]

    cummulativeScores[0][0] = 0
    for refX in range(1, referenceLength+1):
        cummulativeScores[refX][0] = cummulativeScores[refX-1][0] + 1
        bp[refX][0] = DEL
    for hyX in range(1, hypothesisLength+1):
        cummulativeScores[0][hyX] = cummulativeScores[0][hyX-1] + 1
        bp[0][hyX] = INS

    # ---------------- #
    # do the alignment #
    # ---------------- #
    refX = 1

    for refW in splittedTokenSequence[:]:
        hyX = 1
        for hyW in splittedHypothesis[:]:

            newscore = cummulativeScores[refX-1][hyX] + 1                                 # try transition 0: insertion
            if newscore < cummulativeScores[refX][hyX]:
                bp[refX][hyX] = DEL
                cummulativeScores[refX][hyX] = newscore

            if splittedTokenSequence[refX-1] == splittedHypothesis[hyX-1]:                                        # try transition 1: substitution
                newscore = cummulativeScores[refX-1][hyX-1]
                DIFF = EQU
            else:
                newscore = cummulativeScores[refX-1][hyX-1] + 1
                DIFF = SUB
            if newscore < cummulativeScores[refX][hyX]:
                bp[refX][hyX] = DIFF
                cummulativeScores[refX][hyX] = newscore

            newscore = cummulativeScores[refX][hyX-1] + 1                                 # try transition 2: deletion
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

    return (cummulativeScores[refX][hyX], bp, referenceLength, hypothesisLength, splittedTokenSequence, splittedHypothesis)


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

    i = referenceLength   # counter for horizontal position change in DP matrix
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
            subList1 = [splittedTokenSequence[i-1], splittedHypothesis[j-1]]
            subList.insert(0, subList1)  # insert to the beginning of the sub list
            currentField = bp[i-1][j-1]
            i = i - 1
            j = j - 1
        elif currentField == 2:  # in case of ins
            insCount = insCount + 1
            insList.insert(0, splittedHypothesis[j-1])  # insert to the beginning of the ins list
            currentField = bp[i][j-1]  # change position
            j = j - 1
        elif currentField == 3:  # in case of del
            delCount = delCount + 1
            delList.insert(0, splittedTokenSequence[i-1])  # insert to the beginning of the del list
            currentField = bp[i-1][j]
            i = i - 1
        elif currentField == 0:  # in case of equal
            eqCount = eqCount + 1
            currentField = bp[i-1][j-1]
            i = i - 1
            j = j - 1

    InsDelSubCount = [eqCount, insCount, delCount, subCount]  # list with numbers of equals, insertions, deletions and substitutions
    InsDelSub = [InsDelSubCount, insList, delList, subList]   # list with numbers and tokens

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

    i = referenceLength   # counter for horizontal position change in DP matrix
    j = hypothesisLength  # counter for vertical position change in DP matrix

    import collections
    alignment = collections.defaultdict(list)

    while currentField != -1:  # start position with value -1

        # Traverse DP matrix from position with edit distance to start position
        # and output numbers and tokens of equals, ins, del and sub
        # Note: reference on horizontal lines, hypothesis on vertical lines

        if currentField == 1:  # in case of sub
            alignment[i-1].insert(0, (j-1, "sub"))
            currentField = bp[i-1][j-1]
            i = i - 1
            j = j - 1
        elif currentField == 2:  # in case of ins
            alignment[i-1].insert(0, (j-1, "ins"))
            currentField = bp[i][j-1]
            j = j - 1
        elif currentField == 3:  # in case of del
            alignment[i-1].insert(0, (j-1, "del"))
            currentField = bp[i-1][j]
            i = i - 1
        elif currentField == 0:  # in case of equal
            alignment[i-1].insert(0, (j-1, "match"))
            currentField = bp[i-1][j-1]
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


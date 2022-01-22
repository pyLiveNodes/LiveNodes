# -*- coding: utf8 -*-

print("Reading scoring Hierarchical")

import glob
import xml.dom.minidom

# python-lib
import align


def writeMotionPrimitiveCollectionToFile(motionPrimitiveCollection, fileName):
    file = open(fileName, 'w')
    file.write('<MotionPrimitiveCollection>\n')
    for limb in motionPrimitiveCollection:  
        file.write('<Limb name="' + limb + '">\n')
        for sequenceType in motionPrimitiveCollection[limb]:
            file.write('<Sequence name="' + sequenceType + '" ' + 'count="' + str(len(motionPrimitiveCollection[limb][sequenceType])) + '" ')
            counter = 0
            for primitive in motionPrimitiveCollection[limb][sequenceType]:
                print('Counter: ' + str(counter) + 'Writing primitive: ' + primitive)
                if (counter < 10):
                    file.write('motionPrimitive0' + str(counter) + '="' + primitive + '" ')
                elif (counter < 100) & (counter > 9):
                    file.write('motionPrimitive' + str(counter) + '="' + primitive + '" ')
                else:
                    print('ERROR: Can not write more than 100 primitives per limb and sequence')
                counter = counter + 1
            file.write('/>\n')
        file.write('</Limb>\n')
    file.write('</MotionPrimitiveCollection>\n')
    file.close()
    

def createMotionPrimitiveCollectionFromSegmentations():
    # Main program
    
#    segmentationFolder = '/project/AMR/UpperBody/Recognizers/MotionRecognitionVideoBased/082_FluesPosVarMultiLimb/data/segmentations/FluessigUndPositionsVarianz/Britta/dev_cv1/'
#    subfolders = ['Einschenken', 'Reiben', 'Ruehren', 'Schneiden', 'Stampfen']
#    topology = {'whole_body': ['left_arm', 'right_arm']}
#    mainStream = 'whole_body'
#
#fileName = '/project/AMR/UpperBody/Recognizers/MotionRecognitionVideoBased/082_FluesPosVarMultiLimb/data/hierarchicalTestData/MotionPrimitiveCollection.xml';

    segmentationFolder = '/project/AMR/UpperBody/Recognizers/MotionRecognitionVideoBased/083_FluesPosVarNewSegm/data/segmentations/FluessigUndPositionsVarianz/britta/'
    subfolders = ['Einschenken', 'Reiben', 'Ruehren', 'Schneiden', 'Stampfen']
    topology = {}
    mainStream = 'whole_body'

    fileName = '/project/AMR/UpperBody/Recognizers/MotionRecognitionVideoBased/083_FluesPosVarNewSegm/data/hierarchicalTestData/MotionPrimitiveCollection.xml';
    
    motionPrimitiveCollection = dict()
    
    print('Starting MotionPrimitiveCollectionFromSegmentations')
    
    #for each segmentation file
    for subFolder in subfolders:
        
        print('Currentyl in subfolder: ', subFolder)
        
        #Read Segmentations file
        files = glob.glob(segmentationFolder+subFolder+'/*.xml')
        
        print('Parsing files: ', files)
        
        for currentFile in files:
            
            print("Parsing file " + currentFile)
            
            doc = xml.dom.minidom.parse(currentFile)
            
            #Convert xml-structure into objects
            xmlMotionLabeling = doc.getElementsByTagName('MotionLabeling').item(0)
            motionFileName = xmlMotionLabeling.getAttribute('motionFile')
            xmlLimbs = xmlMotionLabeling.getElementsByTagName('Limb')
            for xmlLimb in xmlLimbs:
                limb = xmlLimb.getAttribute('name')
                if (not limb in motionPrimitiveCollection):
                    motionPrimitiveCollection[limb] = dict()
                if (not subFolder in motionPrimitiveCollection[limb]):
                    motionPrimitiveCollection[limb][subFolder] = []
                xmlMotionLabels = xmlLimb.getElementsByTagName('MotionLabel')
                for xmlMotionLabel in xmlMotionLabels:
                    name = xmlMotionLabel.getAttribute('name')
                    if (not name in motionPrimitiveCollection[limb][subFolder]):
                        motionPrimitiveCollection[limb][subFolder].append(name)
            
            
    writeMotionPrimitiveCollectionToFile(motionPrimitiveCollection, fileName)
            
    

def loadMotionPrimitiveCollection(filename):
    print('Loading MotionPrimitiveCollection ', filename)
    doc = xml.dom.minidom.parse(filename)
    
    motionPrimitiveCollection = dict()
    
    #Convert xml-structure into object
    xmlMotionLabeling = doc.getElementsByTagName('MotionPrimitiveCollection').item(0)
    xmlLimbs = xmlMotionLabeling.getElementsByTagName('Limb')
    for xmlLimb in xmlLimbs:
        limb = xmlLimb.getAttribute('name')
        if (not limb in motionPrimitiveCollection):
            motionPrimitiveCollection[limb] = dict()
        xmlMotionSequences = xmlLimb.getElementsByTagName('Sequence')
        for xmlMotionSequence in xmlMotionSequences:
            sequenceType = xmlMotionSequence.getAttribute('name')
            motionPrimitiveCollection[limb][sequenceType] = []
            numberOfPrimitives = xmlMotionSequence.getAttribute('count')
            for primitiveIndex in range(int(numberOfPrimitives)):
                if (primitiveIndex < 10):
                    primitive = xmlMotionSequence.getAttribute('motionPrimitive0'+str(primitiveIndex))
                elif (primitiveIndex < 100) & (primitiveIndex > 9):
                    primitive = xmlMotionSequence.getAttribute('motionPrimitive'+str(primitiveIndex))
                else:
                    print('ERROR: Can not load more than 100 primitives per limb and sequence')
                motionPrimitiveCollection[limb][sequenceType].append(str.lower(str(primitive)))
    return motionPrimitiveCollection

    
"""
Use retrieveFinestStreamRepresentation to calculate input values for this method
"""
def retrieveMostLikelySequenceType(streamNamesList, motionPrimitiveCollection, finestStreamsTokenSequence, tokenStreamIndices, numberOfFinestStreams):
    print('Retrieving most likely sequence type by majority vote')
    #Create empty dict for storing the number of occurrences of the sequence type in the data
    sequenceTypeOccurrences = dict()
    
    if (len(finestStreamsTokenSequence) > 2):
        #TODO Implemented correct weights for finest streams
        print('ERROR: Method does not guarantee to work correctly for more than 2 finest streams. Correct weighting of finest streams based on body hierarchy is not implemented yet. All finest streams are weighted equally')
        return 'Nothing'
    
    #For each motion stream
    for finestStream in range(len(finestStreamsTokenSequence)):
        #For each motion primitive
        for primitiveX in range(len(finestStreamsTokenSequence[finestStream])):
            #Increase count for sequence type by 1/numberOfFinestStreams(tokenStreamIndices(motionPrimitive))
            streamX = tokenStreamIndices[finestStream][primitiveX]
            streamName = streamNamesList[streamX]
            for sequenceType in motionPrimitiveCollection[streamName]:
                if finestStreamsTokenSequence[finestStream][primitiveX] in motionPrimitiveCollection[streamName][sequenceType]:
                    if sequenceType in sequenceTypeOccurrences:
                        sequenceTypeOccurrences[sequenceType] += 1.0/numberOfFinestStreams[streamX]
                    else:
                        sequenceTypeOccurrences[sequenceType] = 1.0/numberOfFinestStreams[streamX]
    #Return most likely sequence type from dict
    mostLikelySequenceType = "Nothing" 
    mostLikelyCount = -1
    for type in sequenceTypeOccurrences:
        print('Sequencetype ' + type)
        if (sequenceTypeOccurrences[type] > mostLikelyCount):
            print('Sequencetype ' + type + ' occurred ' + str(sequenceTypeOccurrences[type]) + ' times')
            mostLikelyCount = sequenceTypeOccurrences[type]
            mostLikelySequenceType = type
    return mostLikelySequenceType

def calculateSequenceAccuracy(tokenSequence, streamNamesList, motionPrimitiveCollection, referenceSequenceType):
    
    splittedTokenSequence = tokenSequence.split();
    
    #Retrieve hierarchy of streams, assumes that hierarchy is the same for reference and hypothesis
    #TODO check whether hierarchies for reference and hypothesis are equal, do we want to handle differing hierarchies?
    [numberOfStreams, numberOfSubStreams, numberOfFinestStreams, firstSubStreamIndex] = align.retrieveHierarchy(splittedTokenSequence)
    
    finestStreamCount = numberOfFinestStreams[0]
    finestStreamsTokenSequence = [ [] for col in range(finestStreamCount) ]
    tokenStreamIndices = [ [] for col in range(finestStreamCount) ]

    align.retrieveFinestStreamRepresentation(0, firstSubStreamIndex, splittedTokenSequence, finestStreamsTokenSequence, tokenStreamIndices, numberOfSubStreams, numberOfFinestStreams)
    
    mostLikelySequenceType = retrieveMostLikelySequenceType(streamNamesList, motionPrimitiveCollection, finestStreamsTokenSequence, tokenStreamIndices, numberOfFinestStreams)
    
    print('ReferenceType is:' + referenceSequenceType)
    print('MostLikeylySequenceType is:' + mostLikelySequenceType)

    if (mostLikelySequenceType == referenceSequenceType):
        return 1
    else:
        return 0

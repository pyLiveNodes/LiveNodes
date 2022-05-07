# -*- coding: utf8 -*-

import copy
import glob
import xml.dom.minidom


class Segmentation():

    def __init__(self, topology):
        self.topology = topology
        primitives = {}

    def createTranscriptionRecursive(self, stream, currentPoint,
                                     streamEndPoint):
        result = ''
        tempPrimitiveIndex = -1
        newEndPoint = streamEndPoint
        while (currentPoint < streamEndPoint):

            #find primitive in Stream with startPoint == currentPoint
            found = False
            #Iteratively append all primitives that match the currentPoint
            if (stream in self.primitives):
                for primitiveIndex in range(len(self.primitives[stream])):
                    primitive = self.primitives[stream][primitiveIndex]

                    if (primitive[1] <= currentPoint):
                        tempPrimitiveIndex = primitiveIndex
                        #if found, append primitive
                        if (primitive[1] == currentPoint):
                            found = True
                            result = result + primitive[0] + ' '
                            currentPoint = primitive[2] + 1

            if (found == False):
                #if has subStreams => search in subStreams (append { | })
                if (stream in self.topology):
                    #Specify the point in time where we have to come back to this level
                    newEndPoint = streamEndPoint
                    if (stream in self.primitives):
                        if (tempPrimitiveIndex <
                                len(self.primitives[stream]) - 1):
                            if (self.primitives[stream][tempPrimitiveIndex +
                                                        1][1] - 1 <
                                    streamEndPoint):
                                newEndPoint = self.primitives[stream][
                                    tempPrimitiveIndex + 1][1] - 1

                    result = result + '{ '

                    for substreamIndex in range(len(self.topology[stream])):
                        substream = self.topology[stream][substreamIndex]
                        result = result + str(
                            self.createTranscriptionRecursive(
                                substream, currentPoint, newEndPoint))
                        if (substreamIndex < len(self.topology[stream]) - 1):
                            result = result + '| '
                    currentPoint = newEndPoint + 1
                    result = result + '} '
                else:
                    raise BaseException("Missing token with startPoint " +
                                        str(currentPoint) + " in stream " +
                                        stream)
        return result

    def retrieveFinalEndPoint(self):
        endPoint = 0
        streams = list(self.topology.keys())
        while (len(streams) > 0):
            newStreams = []

            for stream in streams:
                if (stream in self.primitives):
                    for primitive in self.primitives[stream]:
                        if primitive[2] > endPoint:
                            endPoint = primitive[2]
                #Retrieve streams for lower level

                if (stream in self.topology):
                    for newStream in self.topology[stream]:
                        newStreams.append(newStream)
            streams = newStreams
        return endPoint

    def loadFile(self, fileName):

        self.primitives = {}

        doc = xml.dom.minidom.parse(fileName)

        #Convert xml-structure into objects
        xmlMotionLabeling = doc.getElementsByTagName('MotionLabeling').item(0)
        motionFileName = xmlMotionLabeling.getAttribute('motionFile')
        #TODO Load only if possible
        self.motionSequenceVariant = xmlMotionLabeling.getAttribute(
            'motionSequenceVariant')
        xmlLimbs = xmlMotionLabeling.getElementsByTagName('Limb')
        for xmlLimb in xmlLimbs:
            limb = xmlLimb.getAttribute('name')
            xmlMotionLabels = xmlLimb.getElementsByTagName('MotionLabel')
            limbValues = []
            for xmlMotionLabel in xmlMotionLabels:
                name = xmlMotionLabel.getAttribute('name')
                startPoint = int(xmlMotionLabel.getAttribute('startPoint'))
                endPoint = int(xmlMotionLabel.getAttribute('endPoint'))
                limbValues.append([name, startPoint, endPoint])
            self.primitives[limb] = limbValues

    def getMotionSequenceVariant(self):
        return self.motionSequenceVariant

    def getPrimitives(self):
        return copy.deepcopy(self.primitives)

    def findConcurrentPrimitive(self, stream, primitive):
        if (len(self.topology) > 1):
            raise BaseException(
                "Can not search for concurrent primitives with more than 2 layers"
            )
        if (len(self.topology[list(self.topology.keys())[0]]) != 2):
            raise BaseException(
                "Can not search for concurrent primitives with != 2 child streams"
            )

        #main stream
        if stream in list(self.topology.keys()):
            return primitive
        else:
            concurrentStream = ""
            if (stream == self.topology[list(self.topology.keys())[0]][0]):
                concurrentStream = self.topology[list(
                    self.topology.keys())[0]][1]
            elif (stream == self.topology[list(self.topology.keys())[0]][1]):
                concurrentStream = self.topology[list(
                    self.topology.keys())[0]][0]
            else:
                raise BaseException("Can not find stream " + stream +
                                    " in topology")
            for concurrentPrimitive in self.primitives[concurrentStream]:
                #startPoint of concurrent primitive <= startPoint of primitive
                #and > endPoint of concurrentPrimitive >= startPoint of primitive
                if (concurrentPrimitive[1] <= primitive[1]
                        and concurrentPrimitive[2] >= primitive[1]):
                    return concurrentPrimitive
            raise BaseException("Could not find concurrent primitive for " +
                                str(primitive))

    def findPredecessor(self, streamIndex, primitive):
        if (len(self.topology) > 1):
            raise BaseException(
                "Can not search for concurrent primitives with more than 2 layers"
            )
        if (len(self.topology[list(self.topology.keys())[0]]) != 2):
            raise BaseException(
                "Can not search for concurrent primitives with != 2 child streams"
            )

        #start of sequence
        if (primitive[1] == 0):
            return ['<s>', -2, -1]

        for predPrimitive in self.primitives[list(self.topology.keys())[0]]:
            if (predPrimitive[2] == primitive[1] - 1):
                return predPrimitive
        for predPrimitive in self.primitives[self.topology[list(
                self.topology.keys())[0]][streamIndex]]:
            if (predPrimitive[2] == primitive[1] - 1):
                return predPrimitive
        raise BaseException("Could not find predecessor primitive for " +
                            str(primitive))

    def getConcurrentTrigrams(self, streamIndex):
        lm = dict()
        lm['t'] = 0
        lm[3] = dict()
        lm[2] = dict()

        #For each primitive
        streams = []
        streams.append(list(self.topology.keys())[0])
        streams.append(self.topology[list(
            self.topology.keys())[0]][streamIndex])

        for stream in streams:
            for primitive in self.primitives[stream]:
                #Find primitive concurrent to start of primitive
                concurrentPrimitive = self.findConcurrentPrimitive(
                    stream, primitive)

                #Find predecessor to primitive
                if (streamIndex == 1):
                    concurrentStreamIndex = 0
                else:
                    concurrentStreamIndex = 1
                concurrentPredPrimitive = self.findPredecessor(
                    concurrentStreamIndex, concurrentPrimitive)

                predPrimitive = self.findPredecessor(streamIndex, primitive)

                sequence = concurrentPredPrimitive[0] + ',' + predPrimitive[
                    0] + ',' + primitive[0]
                bigramSequence = concurrentPredPrimitive[
                    0] + ',' + predPrimitive[0]

                #Count trigrams
                if not (sequence in lm[3]):
                    lm[3][sequence] = 1
                    lm['t'] += 1
                else:
                    lm[3][sequence] += 1
                if not (bigramSequence in lm[2]):
                    lm[2][bigramSequence] = 1
                else:
                    lm[2][bigramSequence] += 1

        #Special treatment of end of sequence
        endPrimitive = [
            '</s>',
            self.retrieveFinalEndPoint() + 1,
            self.retrieveFinalEndPoint() + 2
        ]

        if (streamIndex == 1):
            concurrentStreamIndex = 0
        else:
            concurrentStreamIndex = 1
        concurrentPredPrimitive = self.findPredecessor(concurrentStreamIndex,
                                                       endPrimitive)

        predPrimitive = self.findPredecessor(streamIndex, endPrimitive)

        sequence = concurrentPredPrimitive[0] + ',' + predPrimitive[
            0] + ',' + endPrimitive[0]
        bigramSequence = concurrentPredPrimitive[0] + ',' + predPrimitive[0]

        #Count trigrams
        if not (sequence in lm[3]):
            lm[3][sequence] = 1
            lm['t'] += 1
        else:
            lm[3][sequence] += 1
        if not (bigramSequence in lm[2]):
            lm[2][bigramSequence] = 1
        else:
            lm[2][bigramSequence] += 1

        return [lm[3], lm[2]]


# Main program
if __name__ == '__main__':
    segmentationFolder = '/project/AMR/UpperBody/Recognizers/MotionRecognitionVideoBased/082_FluesPosVarMultiLimb/data/segmentations/FluessigUndPositionsVarianz/Britta/dev_cv1/'
    subfolders = ['Einschenken', 'Reiben', 'Ruehren', 'Schneiden', 'Stampfen']
    topology = {'whole_body': ['left_arm', 'right_arm']}
    mainStream = 'whole_body'

    file = open(
        '/project/AMR/UpperBody/Recognizers/MotionRecognitionVideoBased/082_FluesPosVarMultiLimb/data/hierarchicalTestData/transcripts_dev_cv1',
        'w')

    segmentation = Segmentation.Segmentation()

    #for each segmentation file
    for subFolder in subfolders:

        #Read Segmentations file
        files = glob.glob(segmentationFolder + subFolder + '/*.xml')

        for currentFile in files:

            print("Parsing file " + currentFile)

            segmentation.loadFile(currentFile)

            #Find last featureVector index
            finalEndPoint = segmentation.retrieveFinalEndPoint()

            #Start with primitives for whole body
            reference = segmentation.createTranscriptionRecursive(
                mainStream, 0, finalEndPoint)

            #write motionFileName and reference to outputFile

            file.write(motionFileName + ' ' + reference + "\n")

            print("reference is: " + str(reference))

    file.close()

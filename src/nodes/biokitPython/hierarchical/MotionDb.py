import os
import glob

# python-lib
import Database
from . import Segmentation

class MotionDb(Database.Database):
    
    #table names
    sequences = "sequences"
    transcripts = "transcripts"
    splittedTranscripts = "splittedTranscripts"
    
    #create statements
    createTablesStatement = {
    "sequences": "CREATE TABLE sequences ( \
        name TEXT PRIMARY KEY UNIQUE, sequenceType TEXT, sequenceVariant TEXT, person TEXT, \
        fileName TEXT)",
    "transcripts": "CREATE TABLE transcripts (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, transcript TEXT, \
        FOREIGN KEY(name) REFERENCES sequences(name))",
    "splittedTranscripts": "CREATE TABLE splittedTranscripts (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, transcript TEXT, \
        bodyPart TEXT, startPoint INTEGER, endPoint INTEGER, FOREIGN KEY(name) REFERENCES sequences(name))"
    }
    
    def insertSequence(self, name, sequenceType, sequenceVariant, person, fileName):
        #check if person exists
        sqlcmd="SELECT * FROM " + self.sequences + " WHERE name=\"" + name + "\"" 
        self.logsql(sqlcmd)
        result = self.executeStatement(sqlcmd)
        if (result.size() == 0):
            sqlcmd="INSERT INTO " + self.sequences + " (name, sequenceType, sequenceVariant, person, fileName) " \
                + "VALUES ( \"" + name + "\", \"" + sequenceType + "\", \"" + sequenceVariant + "\",\""\
                + person + "\",\"" + fileName + "\" )"
            self.logsql(sqlcmd)
            result = self.executeStatement(sqlcmd)
            self.logres(result)
        else:
            raise LookupError
            
    def insertTranscript(self, name, transcript):
        #This is simply used to check if entry exists
        seqName = self.getUniqueValue(self.sequences, "name", "name",
                                           "\""+name+"\"")
        sqlcmd="INSERT INTO " + self.transcripts + " (name, transcript) "\
            + "VALUES ( \"" + seqName + "\", \"" + transcript + "\" )" 
        self.logsql(sqlcmd)
        self.executeStatement(sqlcmd)
        
    def insertSplittedTranscript(self, name, transcript, bodyPart, startPoint, endPoint):
        #This is only used to check if entry exists
        seqName = self.getUniqueValue(self.sequences, "name", "name",
                                           "\""+name+"\"")
        sqlcmd="INSERT INTO " + self.splittedTranscripts + " (name, transcript, bodyPart, startPoint, endPoint) "\
            + "VALUES ( \"" + seqName + "\", \"" + transcript + "\",\"" +bodyPart+"\"," + str(startPoint) + ", " + str(endPoint) + " )" 
        self.logsql(sqlcmd)
        self.executeStatement(sqlcmd)
        
    def addExperimentFromDirectory(self, directory, personName, mainStream, topology):
        
        #process all matching recordings in directory
        savedWorkingDir = os.getcwd()
        os.chdir(directory)
        sequenceTypes = glob.glob("*")
        count = 0
        
        segmentation = Segmentation.Segmentation(topology)
        
        for sequenceType in sequenceTypes:
            if os.path.isdir(os.path.join(os.getcwd(), sequenceType)):
                os.chdir(sequenceType)
                filelist = glob.glob("*.xml")
                for file in filelist:
                    
                    self.log("Info", "Parsing segmentation file: " + file)
                    
                    prefix = file.partition(".")[0]
                    self.log("Info", "prefix: " + prefix)
                    
                    segmentation.loadFile(file)
                    
                    # retrieve sequenceVariant
                    if (segmentation.getMotionSequenceVariant() != ""):
                        sequenceVariant = segmentation.getMotionSequenceVariant()
                    else:
                        sequenceVariant = sequenceType + re.split("\d", prefix)[2]
                    
                    self.log("Info", "sequenceVariant: " + sequenceVariant)
                    
                                        ######### for ADLDataSet ########
                    #prefix = chopBananaS4R2
                    #subjectIndex = prefix[len(prefix)-3]
                    #self.log("Info", "subjectIndex: " + subjectIndex)
                    #personName = 'S' + subjectIndex
                    
                    #################################
                    
                    #prefix = prefix + '.avi.avi'
                    
                    #createHierarchicalTranscription
                    
                    #Find last featureVector index
                    finalEndPoint = segmentation.retrieveFinalEndPoint()
                    
                    #Start with primitives for whole body
                    transcript = segmentation.createTranscriptionRecursive(mainStream, 0, finalEndPoint)

                    if (transcript.lower().strip() != "sil"):
                    
                        self.insertSequence(prefix, sequenceType, str(sequenceVariant), personName, prefix)
                        
                        self.insertTranscript(prefix, str(transcript))
                        
                        # got through segmentation and insert primitives to database
                        primitives = segmentation.getPrimitives()
                        
                        for bodyPart in primitives:
                            for primitive in primitives[bodyPart]:
                                self.insertSplittedTranscript(prefix, str(primitive[0]), str(bodyPart), primitive[1], primitive[2])
                        
                        count += 1
                    else:
                        self.log("info", "Skipping file " + file + " containing sil")
                os.chdir("..")
        self.log("info", "inserted " + str(count) + " recordings into database.")
        os.chdir(savedWorkingDir)
        
    def retrieveBalancedCrossValidationSetsLeaveOneOut(self, key):
        cvSequences = []
        
        self.log("info", "Retrieving crossvalidation set with Leave one out strategy for key " + str(key))
        sqlcmd = "SELECT DISTINCT " + key + " FROM sequences"
        variances = self.executeStatement(sqlcmd)
        foldIndex = 0
        for res in variances:
            cvSequences.append([])
            sqlcmd = "SELECT name FROM sequences WHERE " + key + " = '" + res[key]+ "'"
            result = self.executeStatement(sqlcmd)
            for res in result:
                cvSequences[foldIndex].append(res['name'])
            foldIndex += 1
        return cvSequences
        
    def retrieveBalancedCrossValidationSets(self, key, folds):
        self.log("info", "Retrieving balanced crossvalidation set with " + str(folds) + " folds for key " + str(key))
        sqlcmd = "SELECT DISTINCT " + key + " FROM sequences"
        self.logsql(sqlcmd)
        variances = self.executeStatement(sqlcmd)
        self.logres(variances)
        
        cvSequences = []
        for i in range(folds):
            cvSequences.append([])
        
        for res in variances:
            sqlcmd = "SELECT name FROM sequences WHERE " + key + " = '" + res[key]+ "' ORDER BY name"
            self.logsql(sqlcmd)
            result = self.executeStatement(sqlcmd)
            self.logres(result)
            foldSize = (len(result) * 1.0) / folds
            iterator = result.__iter__()
            for i in range(folds):
                for j in range(int(round(i*foldSize)),int(round((i+1)*foldSize))):
                    cvSequences[i].append(iterator.next()['name'])
        return cvSequences
    
    def retrieveBalancedCrossValidationSetsForSelection(self, key, folds, selection):
        self.log("info", "Retrieving balanced crossvalidation set with " + str(folds) + " folds for key " + str(key))
        
        sequenceList = ""
        first = True
        for sequence in selection:
            print("sequence "+ sequence)
            if (first == False):
                sequenceList = sequenceList + ","
            sequenceList = sequenceList + "'" + sequence + "'"
            first = False 
        
        sqlcmd = "SELECT DISTINCT " + key + " FROM sequences WHERE name IN ( " + sequenceList + " )" 
        self.logsql(sqlcmd)
        variances = self.executeStatement(sqlcmd)
        self.logres(variances)
        
        cvSequences = []
        for i in range(folds):
            cvSequences.append([])
        
        for res in variances:
            sqlcmd = "SELECT name FROM sequences WHERE " + key + " = '" + res[key]+ "' AND name IN ( " + sequenceList + " ) ORDER BY name" 
            self.logsql(sqlcmd)
            result = self.executeStatement(sqlcmd)
            self.logres(result)
            foldSize = (len(result) * 1.0) / folds
            iterator = result.__iter__()
            for i in range(folds):
                for j in range(int(round(i*foldSize)),int(round((i+1)*foldSize))):
                    cvSequences[i].append(iterator.next()['name'])
        return cvSequences
    
    def getTranscripts(self, sequenceNames, cvIndex):
        assert(cvIndex < len(sequenceNames) and cvIndex >= 0)
        first = True
        sequenceList = ""
        for sequence in sequenceNames[cvIndex]:
            print("sequence "+ sequence)
            if (first == False):
                sequenceList = sequenceList + ","
            sequenceList = sequenceList + "'" + sequence + "'"
            first = False 
             
        sqlcmd = "SELECT * FROM sequences JOIN transcripts on sequences.name=transcripts.name WHERE sequences.name IN ( " + sequenceList + " ) "
            #WHERE name IN ( " + sequenceList + " ) " \#
        self.logsql(sqlcmd)
        result = self.executeStatement(sqlcmd)
        self.logres(result)
        return result
    
    def getSplittedTranscripts(self, sequenceNames, cvIndex):
        assert(cvIndex < len(sequenceNames) and cvIndex >= 0)
        first = True
        sequenceList = ""
        for sequence in sequenceNames[cvIndex]:
            print("sequence "+ sequence)
            if (first == False):
                sequenceList = sequenceList + ","
            sequenceList = sequenceList + "'" + sequence + "'"
            first = False 
             
        sqlcmd = "SELECT * FROM sequences JOIN splittedTranscripts on sequences.name=splittedTranscripts.name WHERE sequences.name IN ( " + sequenceList + " ) "
            #WHERE name IN ( " + sequenceList + " ) " \#
        self.logsql(sqlcmd)
        result = self.executeStatement(sqlcmd)
        self.logres(result)
        return result

    def writeJanusPreDatabase(self, key, dataSet, cvIndex, folds, prefix, bodyPart, resample, partitions, trainSequenceTypes, splitted=False):
        cvSequences = self.retrieveBalancedCrossValidationSets(key, folds)
#        cvSequences = self.retrieveBalancedCrossValidationSetsLeaveOneOut(key)
        if ((dataSet == 'init') or (dataSet == 'train')):
            for part in range(partitions):
#                self.primitiveCounter = dict()
                fileName = os.path.join(prefix, "pre-dbase_"+dataSet+"_part1to"+str(part+1)+"_cv"+str(cvIndex + 1))
                if (os.path.exists(fileName)):
                    os.remove(fileName)
                accumulatedCvSequences = []
                for i in range(len(cvSequences)):
                    if (i != cvIndex):
                        accumulatedCvSequences += cvSequences[i]
                limitedCvSequences = self.retrieveBalancedCrossValidationSetsForSelection(key, partitions, accumulatedCvSequences)
                for j in range(part+1):
                    self.log("info", "Writing " + dataSet + "file for cvIndex " + str(i))
                    self.writeFoldToJanusPreDatabase(limitedCvSequences, j, fileName, bodyPart, resample, trainSequenceTypes, splitted)
        elif (dataSet == 'dev') :
            fileName = os.path.join(prefix, "pre-dbase_"+dataSet+"_cv"+str(cvIndex + 1))
            if (os.path.exists(fileName)):
                os.remove(fileName)
            self.log("info", "Writing " + dataSet + "file for cvIndex " + str(cvIndex))
            self.writeFoldToJanusPreDatabase(cvSequences, cvIndex, fileName, bodyPart, resample, trainSequenceTypes, splitted)

    def writeFoldToJanusPreDatabase(self, cvSequences, cvIndex, fileName, bodyPart, resample, trainSequenceTypes, splitted):
        self.log("info", "Writing fold " + str(cvIndex) + " to Janus PreDatabase")
        if (splitted==True):
            transcripts = self.getSplittedTranscripts(cvSequences, cvIndex)
        else:
            transcripts = self.getTranscripts(cvSequences, cvIndex)
        
        file = open(fileName, 'a')
        
        for transcript in transcripts:
            if ((transcript['transcript'].lower().strip() != 'sil') and (transcript['sequenceType'] in trainSequenceTypes)):
#                if ((transcript['transcript'].lower() in self.primitiveCounter) == False):
#                    self.primitiveCounter[transcript['transcript'].lower()] = 0
#                if (self.primitiveCounter[transcript['transcript'].lower()] < 12):
                    outputText = ""
                    outputText += "{SPK " + transcript['person'] + "}"
                    outputText += " {UTT " + transcript['sequenceType'] + "/" +transcript['name'] + "}"
                    outputText += " {TEXT " + transcript['transcript'].lower() + "}"
                    outputText += " {SEQ " + transcript['sequenceType'] + "}"
                    if (splitted==True):
                        outputText += " {BP " + transcript['bodyPart'] + "}"
			startPoint = int(round(transcript['startPoint'] / resample ))
                        outputText += " {FROM " + str(startPoint) + "}"
			endPoint = int(round(transcript['endPoint'] / resample ))
                        outputText += " {TO " + str(endPoint) + "}"
                        if (bodyPart == transcript['bodyPart']):
                            file.write(outputText + "\n")
                    else:
                        file.write(outputText + "\n")
                        
                    #self.primitiveCounter[transcript['transcript'].lower()] += 1
        
        file.close()
        
        
        
        
    
    

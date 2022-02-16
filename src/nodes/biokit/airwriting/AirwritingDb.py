import glob
import os

import Database

print("AirwritingDB sys path: " + str(os.sys.path))

class AirwritingDb(Database.Database):
    
    #table names
    persons = "persons"
    hand = "hand"
    experiments = "experiments"
    recordings = "recordings"
    
    #create statements
    createSqlStatements = {
    "persons": "CREATE TABLE persons (id INTEGER PRIMARY KEY AUTOINCREMENT, \
        name TEXT UNIQUE, dominantHand INTEGER, \
        FOREIGN KEY(dominantHand) REFERENCES hand(id))",
    "hand": "CREATE TABLE hand (id INTEGER, name TEXT, PRIMARY KEY (id))",
    "experiments": "CREATE TABLE experiments (id INTEGER PRIMARY KEY \
        AUTOINCREMENT, stringId TEXT UNIQUE, personId INTEGER, baseDir TEXT, \
        FOREIGN KEY(personId) REFERENCES persons(id))" ,
    "recordings": "CREATE TABLE recordings (id INTEGER PRIMARY KEY \
        AUTOINCREMENT, reference TEXT, filename TEXT, experimentId INTEGER, \
        FOREIGN KEY(experimentId) REFERENCES experiments(id))"
    }
    
    #views
    # this view contains a filtered version of the recordings table.
    # it contains only entries that do not appear in the corruptfiles table.
    createViewCorrectRecordings = "CREATE VIEW IF NOT EXISTS \
    correctrecordings AS SELECT * FROM recordings EXCEPT SELECT recordings.* \
    FROM recordings, corruptfiles where recordings.id == corruptfiles.recordingId"
    
    # this view contains recording id, reference, person name,
    # experiment string id, base directory and filename of all non corrupted recordings
    createViewAllCorrectRecordings = "CREATE VIEW IF NOT EXISTS allCorrectRecordings AS \
    SELECT correctrecordings.id, reference, name, stringId, baseDir, filename FROM \
    correctrecordings JOIN (SELECT persons.name, experiments.id, experiments.stringId, \
    experiments.personId, experiments.baseDir FROM persons join experiments on \
    persons.id=experiments.personId) persexp on persexp.id=correctrecordings.experimentId"
    
    # this view contains recording id, reference, person name,
    # experiment string id, base directory and filename of all non corrupted recordings
    createViewAllRecordings = "CREATE VIEW IF NOT EXISTS allRecordings AS \
    SELECT recordings.id, reference, name, stringId, baseDir, filename FROM \
    recordings JOIN (SELECT persons.name, experiments.id, experiments.stringId, \
    experiments.personId, experiments.baseDir FROM persons join experiments on \
    persons.id=experiments.personId) persexp on persexp.id=recordings.experimentId"
    
    #view on results containing avg word error rates grouped by cvKeyVal
     
    
    
    
    def createViewCVResults(self, resultTable, viewName, foldNrs, 
                            groupby = "expId" ):
        viewResults = resultTable + "CVResults"
        #viewNiceResults = resultTable + "CVParamResults"
        sqlResults = ("CREATE VIEW IF NOT EXISTS " + viewResults +
            " AS SELECT avg(wer) AS avgwer, sum(cputime) AS sumtime, * FROM " +
            resultTable + " GROUP BY " + groupby +
            " HAVING count(*) = " + str(foldNrs))
        self.executeStatement(sqlResults)
        #problematic because not generally usable
        #sqlNiceResults = ("CREATE VIEW IF NOT EXISTS " + viewNiceResults + " AS " +
        #    "SELECT " + groupby + ", avgwer, " +
        #    "tokenSequenceModelWeight, tokenInsertionPenalty, hypoTopN, " +
        #    "activeNodeTopN, finalNodeTopN, hypoBeam, activeNodeBeam, " +
        #    "finalNodeBeam, trainingIterations, frameOverlap, " +
        #    "frameLengthMultiplier " +
        #    "FROM " + viewResults)
        #self.executeStatement(sqlNiceResults)
        
    
    right = 1
    left = 2
    
    def create(self, filename):
        self.db.openSQLiteDb(filename, BioKIT.Database.CreateNonexisting)
        # create tables
        for statement in self.createSqlStatements.values():
            self.logsql(statement)
            self.executeStatement(statement)
    
      
    def insertPerson(self, name, hand):
        #check if person exists
        sqlcmd="SELECT * FROM " + self.persons + " WHERE name=\"" + name + "\"" 
        result = self.executeStatement(sqlcmd)
        if (result.size() == 0):
            sqlcmd="INSERT INTO " + self.persons + " (name, dominantHand) VALUES " + "( \"" + name + "\", " + str(hand) + " )"
            result = self.executeStatement(sqlcmd)
            self.logres(result)
            
    def insertExperiment(self, stringId, personName, baseDir):
        personId=self.getUniqueValue(self.persons, "id", "name",
                                     "\""+personName+"\"")
        sqlcmd="INSERT INTO " + self.experiments + " (stringId, personId, baseDir) "\
            + "VALUES ( \"" + stringId + "\", " + str(personId) + ", \"" \
            + baseDir +"\" )" 
        self.executeStatement(sqlcmd)
        
    def insertRecording(self, experimentName, reference, filename):
        experimentId = self.getUniqueValue(self.experiments, "id", "stringId",
                                           "\""+experimentName+"\"")
        sqlcmd = "INSERT INTO " + self.recordings + " ( reference, filename, \
            experimentId ) VALUES ( \"" + reference + "\", "\
            + "\"" + filename + "\", " + str(experimentId) + " )"
        self.executeStatement(sqlcmd)
        
    def addExperimentFromDirectory(self, personName, experimentName, directory,
                                   fileSuffix, dominantHand=right):
        self.insertPerson(personName, dominantHand)
        self.insertExperiment(experimentName, personName, directory)
        #process all matching recordings in directory
        savedWorkingDir = os.getcwd()
        os.chdir(directory)
        filelist = glob.glob("*."+fileSuffix)
        count = 0
        for file in filelist:
            #extract reference from filename
            prefix = file.partition(".")[0]
            prefixList = prefix.split("_")
            idxText = prefixList.index("text")
            reference = prefixList[idxText+1]
            self.insertRecording(experimentName, reference, file)
            count += 1
        self.log("info", "inserted " + str(count) + " recordings into database.")
        os.chdir(savedWorkingDir)
        
    def createViewFromSelect(self, key, value, name):
        sqlcmd = "CREATE TEMPORARY VIEW IF NOT EXISTS " + name + " AS\
        SELECT * FROM allRecordings WHERE " + key + " = \"" + str(value) + "\""
        result = self.executeStatement(sqlcmd)
        return result
        
    def createViewsOnKey(self, key, basename):
        sqlcmd = "SELECT DISTINCT " + key + " FROM allRecordings"
        viewkeys = self.executeStatement(sqlcmd)
        viewtables = []
        for view in viewkeys:
            viewname = basename + view[key]
            self.createViewFromSelect(key, view[key], viewname)
            viewtables.append({'table' : viewname, 'value' : view[key]})
        return viewtables
        
        
    def filterRecordings(self, key, value):
        sqlcmd = "SELECT * FROM allRecordings WHERE " + key + "=" + str(value)
        result = self.executeStatement(sqlcmd)
        return result
    
    def createMarkerTable(self, name):
        """Create a table called name to mark individual recordings"""
        
        sqlcmd = "CREATE TABLE IF NOT EXISTS " + name + " (id INTEGER PRIMARY \
        KEY AUTOINCREMENT, recordingId INTEGER, FOREIGN KEY(recordingId) \
        REFERENCES experiments(id))"
        self.executeStatement(sqlcmd)
            
        
    def insertMarker(self, markerTable, fileName):
        """Mark a recording given by filename in the given marker table"""
        
        #check if table exists
        if self.doesTableExist(markerTable):
            sqlcmd = "INSERT INTO " + markerTable + " (recordingId) SELECT id \
            FROM " + self.recordings + " WHERE filename = \"" + fileName + "\""
            sqlres = self.executeStatement(sqlcmd)
        else:
            raise LookupError('Table ' + markerTable + ' does not exist');
        
    def convertToNewDb(self, filename, has_corrupt_rec=False,
                       use_id_as_janusid=False):
        """
        Convert to new style ORM based database (airwriting/db.py)
        
        Sets dominant hand always to 'right'.
        """
        
        from . import db as adb
        airdb = adb.AirDb(filename)
        persons = self.executeStatement("SELECT * FROM persons")
        for person in persons:
            #default dominant hand to right
            newperson = adb.Person(name=person['name'], dominant_hand="right")
            airdb.session.add(newperson)
            try:
                airdb.session.commit()
            except Exception as e:
                print(("Exception (ignoring, performing rollback): %s" % e))
                airdb.session.rollback()
        experiments = self.executeStatement("SELECT experiments.*, \
            persons.name AS personname FROM experiments, persons WHERE \
            experiments.personId == persons.id")
        for experiment in experiments:
            person = airdb.session.query(adb.Person).filter_by(
                        name=experiment['personname']).one()
            print(person)
            #bad hack next to lines
            basedir = '/'.join(experiment['baseDir'].split('/')[3:])
            string_id = experiment['stringId'][1:]
            newexp = adb.Experiment(string_id=string_id,
                                    base_dir=basedir)
            newexp.person = person
            #ranges of experiment types are hardcoded
            numid = int(experiment['stringId'][1:])
            if numid <= 7:
                newexp.type = "number"
            elif numid in [8,9,10,11,12,13,14,15,16,17,18,20]:
                newexp.type = "character"
            elif numid in [19,21,22,23,24,25]:
                newexp.type = "word"
            elif numid in range(52,62):
                newexp.type = "sentence"
            elif numid in range(70,80):
                newexp.type = "sentence"
            airdb.session.add(newexp)
            try:
                airdb.session.commit()
            except Exception as e:
                print(("Exception (ignoring): %s" % e))
                airdb.session.rollback()
        recordings = self.executeStatement(
            "SELECT * FROM allRecordings")
        for rec in recordings:
            experiment = airdb.session.query(adb.Experiment).filter_by(
                        string_id=rec['stringId'][1:]).one()
            newrec = adb.Recording(reference=rec['reference'],
                                   filename=rec['filename'],
                                   experiment=experiment)
            airdb.session.add(newrec)
            airdb.session.commit()
            if use_id_as_janusid:
                janusid = adb.JanusId(recording_id = newrec.id,
                                       janus_id = rec['id'])
                airdb.session.add(janusid)
        if has_corrupt_rec:
            corrupt_recordings = self.executeStatement("SELECT recordings.id \
                FROM corruptfiles, recordings WHERE \
                corruptfiles.recordingId == recordings.id")
            for corrupt_rec in corrupt_recordings:
                recording = airdb.session.query(adb.Recording).filter_by(
                                id=corrupt_rec['id']).one()
                newcorrupt = adb.BrokenRecording(recording=recording)
                airdb.session.add(newcorrupt)
        airdb.session.commit()

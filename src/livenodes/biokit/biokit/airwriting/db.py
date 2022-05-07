import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column
from sqlalchemy import  Integer, String, Float, LargeBinary, Text
"""import the mysql datatypes in order to work with mysql"""
from sqlalchemy.dialects.mysql import \
        BIGINT, BINARY, BIT, BLOB, BOOLEAN, CHAR, DATE, \
        DATETIME, DECIMAL, DECIMAL, DOUBLE, ENUM, FLOAT, INTEGER, \
        LONGBLOB, LONGTEXT, MEDIUMBLOB, MEDIUMINT, MEDIUMTEXT, NCHAR, \
        NUMERIC, NVARCHAR, REAL, SET, SMALLINT, TEXT, TIME, TIMESTAMP, \
        TINYBLOB, TINYINT, TINYTEXT, VARBINARY, VARCHAR, YEAR
from sqlalchemy.orm import sessionmaker
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship, backref

import csv
import itertools
import datetime
import pprint

bsize = 2**24

def log(level, text):
    print("Python log: " + str(datetime.datetime.now()) + " - " + level + ": " + text)
    
def makestr(object, attributes):
    """
    Return a string representation of an object containing the given attributes
    
    If attributes are given that the class doesn't have, an AttributeError is
    thrown.
    
    Keyword arguments:
    object - instance of any class
    attributes - iterable of class attributes to include in the representation
    """ 
    s = "%s\n" % object.__class__
    for attrib in attributes:
        s += "\t%s: %s\n" % (attrib, object.__getattribute__(attrib))
    return s

def write_blob(blob, file):
    with open(file, "w") as fh:
        fh.write(blob)
        
def read_blob(file):
    with open(file) as fh:
        return fh.read()

class StrMixin(object):
    def __str__(self):
        return pprint.pformat(self.__dict__)

Base = declarative_base()
JanusBase = declarative_base()
#ConfigBase = declarative_base()

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class MultipleResultsFound(Error):
    """
    Exception raised if multiple results are found but at max one is expected.
    
    Attributes:
        expr -- query result showing consistency problems
        msg  -- explanation of the error
    """
    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

class ConsistencyError(Error):
    """Exception raised for consistency errors in the database.

    Attributes:
        expr -- query result containing multiple results
        msg  -- explanation of the error
    """
    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

"""
Database interfaces for the airwriting system. Two main independent databases
exist:
AirDb - stores all information on experiments and recorded data
ConfigDb - stores information on evaluations and results
"""

def get_or_create(session, model, **kwargs):
    """
    Returns existing entries or creates them if they do not exist
    """
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        print(("%s already existed" % instance))
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        print(("%s was created" % instance))
        return instance

class Recording(Base):
    """
    Represents one airwriting recording in an AirDb database.
    
    There is a many-to-one relationship with Experiment.
    
    Class attributes:
    id - integer id of the recording (must be unique)
    text - text that was actually written during recording
    experiment_id - id of the experiment this recording belongs to
    experiment - the experiment this recording belongs to
    filename - name of the file in which the recording is stored 
    """
    __tablename__ = "recordings"
    id = Column(Integer, primary_key=True)
    reference = Column(String(200), nullable=False)
    filename = Column(String(200), nullable=False, unique=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), 
                           nullable=False)
    experiment = relationship("Experiment", backref=backref("recordings"))
    
    def __repr__(self):
        return ("<Recording(%s, %s, %s)>" 
              % (self.reference, self.filename, self.experiment))
        
class Experiment(Base):
    """
    Represents one recording session of airwriting data.
    
    There is a many-to-one relationship to Person.
    There is a one-to-many relationship to Recording.
    
    Class attributes:
    id - integer id of the experiment (primary key)
    expid - string id of the experiment
    baseDir - directory where the data files are stored
    person_id - the person_id of this experiments subject
    person - the person who did this experiment
    """
    __tablename__ = "experiments"
    id = Column(Integer, primary_key = True)
    string_id = Column(String(50), unique=True)
    base_dir = Column(String(512), nullable=False)
    type = Column(String(30), nullable=False)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    person = relationship("Person", backref=backref("experiments"))
    
    def __repr__(self):
        return ("<Experiment(%s, %s, %s)>" 
                % (self.base_dir, self.person, self.string_id))
    
class Person(Base):
    """
    Represents one subject.
    
    There is a one-to-many relationship to Experiment.
    
    Class attributes:
    id - integer id of the person (primary key)
    name - name of the person
    dominant hand - either right or left
    """
    __tablename__ = "persons"
    id = Column(Integer, primary_key = True)
    name = Column(String(50), nullable=False, unique=True)
    dominant_hand = Column(String(20), nullable=False)
        
    def __repr__(self):
        return ("<Person(%s, %s)>"
                % (self.name, self.dominant_hand))
        
class BrokenRecording(Base):
    """
    Represents one recording, that is somehow broken.
    
    """
    __tablename__ = "broken_recordings"
    id = Column(Integer, primary_key=True)
    recording_id = Column(Integer, ForeignKey("recordings.id"), nullable=False)
    recording = relationship("Recording", backref=backref("broken_recording",
                                                          uselist=False))
    
class JanusId(Base):
    """
    Maps a recording id to an old Janus style id
    """
    __tablename__ = "janus_ids"
    id = Column(Integer, primary_key=True)
    janus_id = Column(String(50), nullable=False, unique=True)
    recording_id = Column(Integer, ForeignKey("recordings.id"), nullable=False)
    recording = relationship("Recording", backref=backref("janus_id",
                                                          uselist=False))
    
class AirDb(object):
    """
    SQLite database containing airwriting recordings
    """
    def __init__(self, connstring):
        """
        Constructor takes a connection string as argument and creates a session.
        
        Typical connection strings could be:
        sqlite:///<path-to-sqlitefile>
        postgresql://<username>:<password>@<host>/<dbname>
        
        Keyword arguments:
        connstring - the sqlalchemy connection string
        """
        self.engine = sqlalchemy.create_engine(connstring, pool_recycle=72000)
        Base.metadata.create_all(self.engine)
        self.SessionMaker = sessionmaker(bind = self.engine)
        self.session = self.SessionMaker()
        
    def close(self):
        """
        Closes the session.
        """
        self.session.close()
        
    def insert_unique(self, instance):
        """
        Insert if not exists under uniqueness constraint
        
        Does ignore IntegrityError exceptions from the database, as they 
        appear on a violated uniqueness constraint. This behaviour is race
        condition save, i.e. if a concurrent inserts of the same person do not
        lead to exceptions.
        
        WARNING: This ignores all IntegrityErrors, maybe those errors are also
        raised in other conditions than violated uniqueness, which I am not
        aware of.
        
        Keyword arguments:
        instance - Instance of a database mapping class to be added
        """
        print(("Insert %s" % (instance)))
        try:
            self.session.add(instance)
            self.session.commit()
        except sqlalchemy.exc.IntegrityError as e:
            self.session.rollback()
            print(instance)
            print(("Data %s already exists (Exception: %s)" % (instance, e)))
            

    def insert_complete(self, person, experiment, experiment_type, reference,
                        filename, basedir, dominant_hand = "right",
                        janusid = None):
        """
        Insert a complete recording including person and experiment.
        
        If the corresponding person or experiment does not exist it is created.
        If the recording already exists, an IntegrityException is thrown. If 
        a janusid is provided, a JanusId object is created. If the janusid 
        already exists, an IntegrityException is thrown.
        
        Keyword arguments:
        person - name of the person
        experiment - string id of the experiment
        experiment_type - string description of experiment type
        reference - reference text encoded in the recording
        filename - name of the data file
        basedir - base directory of experiment
        dominant_hand - the hand which was used (default: right)
        janusid - corresponding id of recording in janus database
        
        """
        newperson = Person(name=person, dominant_hand=dominant_hand)
        self.insert_unique(newperson)
        newperson = self.session.query(Person).filter(Person.name==person).one()
        newexperiment = Experiment(string_id=experiment, base_dir=basedir,
                                   person=newperson, type=experiment_type)
        self.insert_unique(newexperiment)
        newexperiment = self.session.query(Experiment).filter(
                            Experiment.string_id==experiment).one()
        newrecording = Recording(reference=reference, filename=filename,
                                 experiment=newexperiment)
        self.session.add(newrecording)
        self.session.commit()
        if janusid:
            newrecording = self.session.query(Recording).filter(
                            Recording.filename==filename).one()
            newjanusid = JanusId(recording_id=newrecording.id,
                                 janus_id=janusid)
            self.session.add(newjanusid)
            self.session.commit()
            
    def load_janus_dataset(self, filename, name=None):
        """
        Load a textfile containing janus ids and save as dataset.
        
        The file must contain one line containing the Janus ids seperated by
        blanks.
        """
        with open(filename) as fh:
            idstring = fh.readline().strip()
        ids = idstring.split()
        recordings = []
        for id in ids:
            janusid = self.session.query(JanusId).filter(
                            JanusId.janus_id==id).one()
            recording = self.session.query(Recording).filter(
                            Recording.id==janusid.recording_id  ).one()
            recordings.append(recording)
        dataset = Dataset(recordings=recordings, name=name)
        self.insert_unique(dataset)
        
        
    def write_janus_dataset(self, dataset, filename):
        """
        Write a given dataset as a janus readable set file (using janus ids)
        
        Keyword arguments:
        dataset - an instance of Dataset
        filename - path to set file to write
        """
        with open(filename, 'w') as fh:
            #the following statement was found with trial & error due to a lack
            #of in-depth knowledge of sqlalchemy, make it better if you can!
            results = self.session.query(Recording, JanusId).\
                    join(Dataset.recordings).\
                    join(JanusId).\
                    filter(Dataset.id == dataset.id).all()
            ids = [x[1].janus_id for x in results]
            log("Info", "Writing janus ids for dataset %s with %s ids to file %s." 
                            % (dataset.name, len(ids), filename))
            s = " ".join(ids)
            fh.write(s)
                
    def clean_all_trained_models(self):
        """
        Delete everything except the data corpus.
        
        Does not delete any corresponding files.
        """
        self.session.query(ModelParameters).delete()
        self.session.commit()
        
    def clean_job(self, job, delete_files = True):
        if delete_files:
           pass 
        
    def clean_jobs(self):
        """
        Clear the jobs table
        """
        self.session.query(Job).delete()
        self.session.commit()
        
    def clean_results(self):
        """
        Delete all results
        """
        self.session.query(Result).delete()
        self.session.commit()
        
    def find_modelparameters(self, config, iteration):
        """
        Look for existing modelparameters matching the giving configuration.
        
        Equality is defined by an exact match of configurations.
        
        Keyword arguments:
        session - valid db.AirDb.session
        config - instance of db.Configuration
        iteration - number of training iterations
        
        Raises MultipleResultsFound if more than one matching ModelParameters
            object is found
        """  
        result = self.session.query(ModelParameters).filter_by(
                                configuration = config,
                                iteration = iteration).all()
        if len(result) == 0:
            return None
        elif len(result) == 1:
            return result[0]
        else:
            raise MultipleResultsFound(result,
                "found %s modelparameters, but only one at max is expected" %
                (len(result),))
        
    def find_equal_training_modelsparameters(self, config, iteration):
        """
        Check if models with the same configuration exist. Equality of 
        configuration is defined as equality of all training relevant parameters:
        data_basedir
        janusdb_name
        atomset
        basemodel
        preprocessing
        topology
        trainset
        transcriptkey
        iteration
        
        That means no equality is necessary for decoding specific values:
        dictionary
        vocabulary
        contextmodel
        ibisconfig
        biokitconfig
        testset 
    
        Returns the model iff one was found, None otherwise.
    
        Raises db.MultipleResultsFound if more than one model was found
    
        Keyword arguments:
        session - A db.AirDb.session object
    
        """
        log("Info", "Check for existing models with same training configuration")
        foundConfig = None
        result = self.session.query(ModelParameters).\
                    join(ModelParameters.configuration).\
                    filter(Configuration.data_basedir == config.data_basedir).\
                    filter(Configuration.janusdb_name == config.janusdb_name).\
                    filter(Configuration.atomset == config.atomset).\
                    filter(Configuration.basemodel == config.basemodel).\
                    filter(Configuration.preprocessing == config.preprocessing).\
                    filter(Configuration.topology == config.topology).\
                    filter(Configuration.trainset == config.trainset).\
                    filter(Configuration.transcriptkey == config.transcriptkey).\
                    filter(ModelParameters.iteration == iteration).\
                    all()
        if len(result) == 1:
            return result[0]
        elif len(result) > 1:
            raise MultipleResultsFound(
                result,
                "Found %s possible trained models: %s" % (len(result), result))
        
            

class JanusRecording(JanusBase):
    """
    Represents one recording in a flat Janus style database
    """
    __tablename__ = "recordings"
    id = Column(Integer, primary_key=True)
    person = Column(String(30))
    expid = Column(String(30))
    text = Column(String(512))
    filename = Column(String(512))
    janusid = Column(String(50))        
        

class JanusDb(object):
    """
    SQLite database containing flat recordings with janus ids
    """
    def __init__(self, sqlitefile):
        """
        Constructor takes the sqlite file as argument and creates a session.
        
        Keyword arguments:
        sqlitefile - sqlite file containing the database or empty file to 
                     create new database
        """
        self.engine = sqlalchemy.create_engine('sqlite:///'+sqlitefile)
        JanusBase.metadata.create_all(self.engine)
        self.SessionMaker = sessionmaker(bind = self.engine)
        self.session = self.SessionMaker()

    def insert_into_airdb(self, airdb, experiment_type):
        """
        Insert all data into an AirDb session.
        
        Sets dominant hand to right by default.
        
        Keyword arguments:
        airdb - an instance of AirDb
        basepath - basepath of all experiments, will be appended by 
                   <experiment_string_id>/data
        experiment_type - string description of experiemnt type (e.g. word)
        """
        recordings = self.session.query(JanusRecording).all()
        for janusrec in recordings:
            basedir = "/".join(["v"+str(janusrec.expid), "data"])
            airdb.insert_complete(janusrec.person, janusrec.expid,
                                  experiment_type,
                                  janusrec.text, janusrec.filename,
                                  basedir, janusid=janusrec.janusid)
            
    def insert_from_csv(self, csvfile, basedir, reference_key='text'):
        """
        Read a csv file and insert data into database.
        
        Format is key,value,key,value,... That means, the delimiter is ','
        and no header is given in the csv file. The keys must be equal in 
        every line, otherwise an error is thrown.
        
        Keyword arguments:
        csvfile - an open file handle to the csv file
        basedir - 
        """
        csvreader = csv.reader(csvfile, delimiter=',')
        lines = [x for x in csvreader]
        keys = lines[0][::2]
        #sanity check
        for line in lines:
            if keys != line[::2]:
                raise Exception()
        for line in lines:
            linedict = dict(list(zip(line[::2], line[1::2])))
            janusrec = JanusRecording(person = linedict['person'],
                                      expid = linedict['expid'],
                                      text = linedict[reference_key],
                                      filename = linedict['filename'],
                                      janusid = linedict['janusid'])
            self.session.add(janusrec)
        self.session.commit()
            
    #def populate_from_airdb(self, airdb, basepath):
    #    """
    #    Populate a Janus recordings database from a AirDb database
    #    
    #    Keyword arguments:
    #    airdb - an instance of AirDb containing the data
    #    basepath - path to prepend before Experiment.base_dir
    #    """
    #    recordings = airdb.session.query(Recording).all()
    #   for rec in recordings:
    #       janusrec = db.JanusRecording()
    #       janusrec.person = rec.experiment.person.name
    #       janusrec.stringId = 
            
##############################################################################
#
# Configuration tables
#
##############################################################################

class ContextModelType(Base, StrMixin, object):
    """
    Reference Table for the different types of context models
    """
    __tablename__="contextmodeltypes"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))




class ContextModel(Base, StrMixin, object):
    """Stores relevant information for a tokensequence model"""
    __tablename__="contextmodels"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    file = Column(String(200), unique=True)
    type_id = Column(Integer,ForeignKey("contextmodeltypes.id"),nullable=False)
    type = relationship("ContextModelType", backref=backref("contextmodels"))
    __table_args__ = (UniqueConstraint('name', 'type_id'),)
  
    
class Dictionary(Base, StrMixin, object):
    """Stores information on the used dictionary"""
    __tablename__="dictionaries"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    file = Column(String(200), unique=True)
    
    
class Vocabulary(Base, StrMixin, object):
    """Stores information on the used vocabulary"""
    __tablename__="vocabularies"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    file = Column(String(200), unique=True)
    
    
class AtomSet(Base, StrMixin, object):
    """Stores information on the used atoms"""
    __tablename__="atomsets"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    enumeration = Column(String(256))
    
    
class ModelParameters(Base, object):
    """
    Stores information on all the model parameters and the number of iteration
    they have been trained
    """
    __tablename__="modelparameters"
    id = Column(Integer, primary_key=True)
    gaussian_desc = Column(LargeBinary(bsize))
    gaussian_data = Column(LargeBinary(bsize))
    mixture_desc = Column(LargeBinary(bsize))
    mixture_data = Column(LargeBinary(bsize))
    distrib_tree = Column(LargeBinary(bsize))
    topologies = Column(LargeBinary)
    topology_tree = Column(LargeBinary)
    transitions = Column(LargeBinary)
    phones = Column(LargeBinary)
    iteration = Column(Integer)
    configuration_id = Column(Integer, ForeignKey("configurations.id", 
                              use_alter=True, name="config_id_fk"),
                              nullable=False)
    configuration = relationship("Configuration",
                              primaryjoin="(ModelParameters.configuration_id==Configuration.id)",
                              backref=backref("modelparameters"))
    #__table_args__ = UniqueConstraint('')
    
    def read_from_files(self, gaussian_desc, gaussian_data, mixture_desc,
                        mixture_data, distrib_tree, topologies, topology_tree,
                        transitions, phones):
        self.gaussian_desc = read_blob(gaussian_desc)
        self.gaussian_data = read_blob(gaussian_data)
        self.mixture_desc = read_blob(mixture_desc)
        self.mixture_data = read_blob(mixture_data)
        self.distrib_tree = read_blob(distrib_tree)
        self.topologies = read_blob(topologies)
        self.topology_tree = read_blob(topology_tree)
        self.transitions = read_blob(transitions)
        self.phones = read_blob(phones)
        
    def read_from_biokit_files(self, gaussian_desc, gaussian_data, mixture_desc,
                        mixture_data, distrib_tree, topologies, topology_tree,
                        phones):
        """
        Reads in files in biokit format
        """
        self.gaussian_desc = read_blob(gaussian_desc)
        self.gaussian_data = read_blob(gaussian_data)
        self.mixture_desc = read_blob(mixture_desc)
        self.mixture_data = read_blob(mixture_data)
        self.distrib_tree = read_blob(distrib_tree)
        self.topologies = read_blob(topologies)
        self.topology_tree = read_blob(topology_tree)
        self.phones = read_blob(phones)

    def __str__(self):
        return ("ModelParameters: configuration_id = %s, iteration = %s" 
                % (self.configuration_id, self.iteration))

    
    def __repr__(self):
        return ("<ModelParameters: configuration_id = %s, iteration = %s>" 
                % (self.configuration, self.iteration))
    
class PreProcessing(Base, StrMixin, object):
    """
    Stores the name of the used preprocessing method.
    """
    __tablename__="preprocessings"
    #name = Column(String, primary_key=True)
    id = Column(Integer, primary_key=True)
    type = Column(String(100))
    biokit_desc = Column(String(256))
    janus_desc = Column(String(256))
    janus_access = Column(String(256))

    __mapper_args__ = {
            'polymorphic_identity': 'PreProcessing',
            'polymorphic_on': type
    }
    
class PreProStandard(PreProcessing, StrMixin, object):
    """
    The standard airwriting preprocessing configuration
    """
    __tablename__="preprostandardconfigs"
    id = Column(Integer, ForeignKey('preprocessings.id'), primary_key=True)
    windowsize = Column(Integer, nullable=False)
    frameshift = Column(Integer, nullable=False)
    filterstring = Column(String(50), nullable=False)
    channels = Column(String(100), nullable=False)
    meansub = Column(String(50), nullable=False)
    feature = Column(String(50), nullable=False)

    __mapper_args__ = {'polymorphic_identity': 'PreProStandard'}
    __table_args__ = (UniqueConstraint('windowsize', 'frameshift',
                                       'filterstring', 'channels', 'meansub',
                                       'feature' ),)
    
    def janusConfigStr(self):
        s = 'windowsize %s\n' % (self.windowsize)
        s += 'frameshift %s\n' % (self.frameshift)
        s += 'filter {%s}\n' % (self.filterstring)
        s += 'channels {%s}\n' % (self.channels)
        s += 'meansub "%s"\n' % (self.meansub)
        s += 'feature "%s"\n' % (self.feature) 
        return s
    
    #def __str__(self):
    #    return ("PreProStandard: windowsize=%s, frameshift=%s, filterstring

    
class TopologyConfig(Base, StrMixin, object):
    """
    Stores information on the HMM topology
    """
    __tablename__="topologies"
    id = Column(Integer, primary_key=True)
    hmmstates = Column(Integer)
    hmm_repos_states = Column(Integer)
    gmm = Column(Integer)
    gmm_repos = Column(Integer)
    __table_args__ = (UniqueConstraint('hmmstates', 'hmm_repos_states',
                                       'gmm', 'gmm_repos'),)
    

class IbisConfig(Base, StrMixin, object):
    """
    Ibis decoder specific parameters
    """
    __tablename__="ibisconfigs"
    id = Column(Integer, primary_key=True)
    wordPen = Column(Integer)
    lz = Column(Integer)
    wordBeam = Column(Integer)
    stateBeam = Column(Integer)
    morphBeam = Column(Integer)
    __table_args__ = (UniqueConstraint('wordPen', 'lz', 'wordBeam', 'stateBeam',
                                       'morphBeam'),)
        
class BiokitConfig(Base, StrMixin, object):
    """
    BioKit decoder specific parameters
    """
    __tablename__="biokitconfigs"
    id = Column(Integer, primary_key=True)
    token_insertion_penalty = Column(Integer)
    languagemodel_weight = Column(Integer)
    hypo_topn = Column(Integer)
    hypo_beam = Column(Integer)
    final_hypo_beam = Column(Integer)
    final_hypo_topn = Column(Integer)
    lattice_beam = Column(Integer)
    __table_args__ = (UniqueConstraint('token_insertion_penalty',
                                       'languagemodel_weight', 'hypo_topn',
                                       'hypo_beam', 'final_hypo_beam', 
                                       'final_hypo_topn', 'lattice_beam'),)

class Dataset(Base, object):
    """
    Stores the ids of datasets
    """
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    recordings = relationship("Recording", secondary=lambda:dataset_association)
    
    def __str__(self):
        return ("Dataset: id=%s, name=%s, length=%s" % (self.id, self.name,
                                                        len(self.recordings)))
    
    def __repr__(self):
        return ("<Dataset(%s, %s)>" 
                % (self.name, self.recordings))
    

dataset_association = Table('dataset_association', Base.metadata,
    Column('set_id', Integer, ForeignKey('datasets.id')),
    Column('reording_id', Integer, ForeignKey('recordings.id'))
)
    

            
crossval_association = Table('crossval_association', Base.metadata,
    Column('crossvalidation_id', Integer, ForeignKey('crossvalidations.id')),
    Column('configuration_id', Integer, ForeignKey('configurations.id'))
)

class CrossValidation(Base, StrMixin, object):
    __tablename__="crossvalidations"
    id = Column(Integer, primary_key=True)
    nr_folds = Column(Integer)
    configurations = relationship("Configuration",
                                  secondary=crossval_association)


class Configuration(Base):
    """
    Stores all relevant information to reproduce a training and evaluation
    """
    __tablename__="configurations"
    id = Column(Integer, primary_key=True)
    #files and paths
    data_basedir = Column(String(256))
    janusdb_name = Column(String(256))
    atomset_id = Column(Integer, ForeignKey("atomsets.id"))
    atomset = relationship("AtomSet", backref=backref("configurations"))
    dictionary_id = Column(Integer, ForeignKey("dictionaries.id"))
    dictionary = relationship("Dictionary", backref=backref("configurations"))
    vocabulary_id = Column(Integer, ForeignKey("vocabularies.id"))
    vocabulary = relationship("Vocabulary", backref=backref("configurations"))
    contextmodel_id = Column(Integer, ForeignKey("contextmodels.id"))
    contextmodel = relationship("ContextModel",
                                backref=backref("configurations"))
    basemodel_id = Column(Integer, ForeignKey("modelparameters.id"))
    basemodel = relationship("ModelParameters", 
                             primaryjoin=(basemodel_id==ModelParameters.id),
                             backref=backref("base_of_configurations"))
    
    preprocessing_id = Column(Integer, ForeignKey("preprocessings.id"), 
                              nullable=False)
    preprocessing = relationship("PreProcessing", 
                                 backref=backref("configurations"))
    topology_id = Column(Integer, ForeignKey("topologies.id"), nullable=False)
    topology = relationship("TopologyConfig", backref=backref("configurations"))
    ibisconfig_id = Column(Integer, ForeignKey("ibisconfigs.id"))
    ibisconfig = relationship("IbisConfig", backref=backref("configurations"))
    biokitconfig_id = Column(Integer, ForeignKey("biokitconfigs.id"))
    biokitconfig = relationship("BiokitConfig",
                                backref=backref("configurations"))
    iterations = Column(Integer)
    trainset_id = Column(Integer, ForeignKey("datasets.id"))
    trainset = relationship("Dataset", primaryjoin=(trainset_id==Dataset.id),
                            backref=backref("trainset_configs"))
    testset_id = Column(Integer, ForeignKey("datasets.id"))
    testset = relationship("Dataset", primaryjoin=(testset_id==Dataset.id),
                           backref=backref("testset_configs"))
    transcriptkey = Column(String(50))
    
    def __str__(self):
        #attribs = ("id", "data_basedir", "janusdb_name", "atomset", "dictionary",
        #           "vocabulary", "contextmodel", "basemodel", "preprocessing",
        #           "topology", "ibisconfig", "biokitconfig", "iterations", 
        #           "trainset", "testset", "transcriptkey")
        attribs = ("id", "basemodel", "ibisconfig", "biokitconfig", "iterations",
                   "trainset", "testset")
        return makestr(self, attribs)
    
#class JobStatus(Base):
#    id
#    desc
    
class Job(Base, StrMixin, object):
    """
    Stores information and status on job to run or running
    """
    __tablename__="jobs"
    id = Column(Integer, primary_key=True)
    configuration_id = Column(Integer, ForeignKey("configurations.id"))
    configuration = relationship("Configuration",
                                 backref=backref("jobs"))
    status = Column(String(30))
    cputime = Column(Float)
    host = Column(String(50))
    
    def __repr__(self):
        return ("<Job(%s, %s, %s, %s)>" % (self.configuration_id, self.status,
                                           self.cputime, self.host))
    

class Result(Base, StrMixin, object):
    """
    Stores the result of an evaluation
    """
    __tablename__="results"
    id = Column(Integer, primary_key=True)
    git_rev = Column(String(100))
    ter = Column(Float)
    configuration_id = Column(Integer, ForeignKey("configurations.id"))
    configuration = relationship("Configuration", backref=backref("results"))
    iteration = Column(Integer)
    # FIXME: wrong unique constraint, does nothing
    UniqueConstraint('configuration_id', 'iteration')
    
    def __repr__(self):
        return ("<Result(%s, %s, %s, %s)>"
                % (self.git_rev, self.ter,
                   self.configuration_id, self.iteration))

class ResultList(Base, StrMixin, object):
    """
    Stores detailed list of results.
    """
    __tablename__="resultlists"
    result_id = Column(Integer, ForeignKey("results.id"), primary_key=True)
    result = relationship("Result", backref=backref("resultlist"))
    resjson = Column(Text)
    
class ErrorBlaming(Base, StrMixin, object):
    """
    Stores results of the error blaming.
    """
    __tablename__="errorblaming"
    result_id = Column(Integer, ForeignKey("results.id"), primary_key=True)
    result = relationship("Result", backref=backref("errorblaming"))
    blamelog = Column(Text)
    confusionmap = Column(Text)


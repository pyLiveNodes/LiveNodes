'''
Created on 29.02.2012

@author: camma
'''

import collections
import itertools
import os
import pickle
import pprint
import shutil

# python-lib
from . import airwritingUtil as airUtil

class Config(collections.MutableMapping):
    '''
    Base class to store all sorts of configuration information
    
    All configuration information is stored as key value pairs. The class 
    exposes a Mapping interface and therefore can be used like a dictionary.
    The data can be written to and read from files in binary and text format.
    '''  
    
    _values = {}
    _optionality = {}
      
    def __init__(self):
        self._values = {}
        self._optionality = {}
    #abstract methods
    def __getitem__(self, key):
        return self._values[key]
    
    def __setitem__(self, key, value):
        # TODO: if key not exists set optionality to false by default 
        self._values[key] = value
        
    def __delitem__(self, key):
        return self._values.pop(key)
    
    def __len__(self):
        return len(self._values)
    
    def __iter__(self):
        return iter(self._values)
        
    def setoptional(self, key, isOptional):
        self._optionality[key] = isOptional
    
    def saveFile(self, filename):
        """Save config to file in pickle format."""
        with open(filename, "w") as fh:
            pickle.dump(self, fh)
    
    def loadFile(self, filename):
        """Load config from file in pickle format."""
        with open(filename, "r") as fh:
            self = pickle.load(fh)
        
    def saveTxtFile(self, filename):
        """Save config in file in text format."""
        with open(filename, "w") as f:
            for key, value in self._values.items():
                f.write(key + "=" + str(value) + "\n")
    
    def loadTxtFile(self, filename):
        """Load config from file given in text format."""
        with open(filename, "r") as f:
            for line in f.readlines():
                words = [w.strip() for w in line.split("=")]
                print(words[0] + " = " + words[1])
                try:
                    #try to eval string for lists, dicts, ... given as string
                    self._values[words[0]] = eval(words[1])
                except NameError:
                    #assume a string
                    self._values[words[0]] = words[1]
                except SyntaxError:
                    self._values[words[0]] = words[1]
    
    def generateConfigTable(self, db, tableName):
        """
        Create a table with one column for each config parameter.
        
        Keyword arguments:
        db -- Database object
        tableName -- Name of the table to be created
        """
        #construct table creation sql query
        sqlcmd = ("CREATE TABLE IF NOT EXISTS " + tableName + "(id INTEGER PRIMARY" +
        " KEY AUTOINCREMENT ")
        for key in self:
            if type(self[key]) == int:
                sqlcmd += ", " + key + " INTEGER"
            elif type(self[key]) == float:
                sqlcmd += ", " + key + " FLOAT"
            else:
                sqlcmd += ", " + key + " TEXT"
        sqlcmd += ")"
        db.executeStatement(sqlcmd)
        
    def _sqlize(self, x):
        """
        Generate a sql-style string for given value.
        
        Keyword arguments:
        x -- variable to be converted
        
        Returns either a number as string if the given value is of type float,
            int or long, or otherwise x converted to a string enclosed in ' ' 
            quotation marks.
        """
        if type(x) in [float, int, int]:
            return str(x)
        else:
            s = str(x)
            #not really robust, at least I'm not sure --> use ORM
            sqlized = s.replace("'", '"') # sqlite needs double quotes 
            return "\'" + str(sqlized) + "\'"
    
    def insertIntoDb(self, db, tableName):
        print("config values: ")
        #for k in self: print k  
        sqlcmd = "INSERT INTO " + tableName + " ( "
        sqlcmd += ", ".join(iter(self.keys()))
        sqlcmd += " ) VALUES ( "
        sqlcmd += ", ".join([self._sqlize(x) for x in self.values()])
        sqlcmd += " )"
        ret = db.executeStatement(sqlcmd)
        print(ret)
        
    def countInDb(self, db, tableName, ignorelist):
        params = [(x,y) for x,y in list(self.items()) if x not in ignorelist]
        paramList = [x + "=" + self._sqlize(y) for x,y in params]
        sqlcmd = "SELECT count(*) AS count FROM " + tableName + " WHERE "
        sqlcmd += " AND ".join(paramList)
        ret = [x for x in db.executeStatement(sqlcmd)]
        assert len(ret) == 1
        print(ret)
        return ret[0]['count']
    
    def getFromDb(self, db, table, rowid):
        configResults = db.executeStatement("SELECT * FROM " + table +
                                            " WHERE id = " + rowid)
        configResults = [x for x in configResults]
        configRes = configResults[0]
        #rename primary key, otherwise will conflict when inserting to other table
        configRes['orig_id'] = configRes.pop('id')
        pprint.pprint([(k, v, type(v)) for k,v in list(configRes.items())])
        for key, value in list(configRes.items()):
            #strval = str(value)
            try:
                if type(value) == str:
                    #try to eval string for lists, dicts, ... given as string
                    #inherently unsafe and unpredictable (e.g. '011' -> 9 (octal))
                    #must be refactored using an ORM (sqlalchemy)!!!!
                    print(("trying to evaluate string: " + value))
                    evalval = eval(value)
                    print(("got type (" + str(type(evalval)) + ") with value " + str(evalval)))
                    if type(evalval) in [list, dict]:
                        self._values[key] = evalval
                    else:
                        #dirty hack to exclude undesired conversions via eval
                        #assume string for all that was not eval'ed to list or dict
                        self._values[key] = value
                else:
                    self._values[key] = value
            except NameError as ne:
                #assume a string
                print(("NameError: " + str(ne)))
                self._values[key] = str(value)
            except SyntaxError as se:
                print(("SyntaxError: " + str(se)))
                self._values[key] = str(value)
            
        
class ConfigGenerator:
    """
    Manage parameter ranges and return all possible combinations of them.
    
    The parameter ranges are set via the property param_ranges. To set 1,3,5 
    for an imaginary parameter x and a given ConfigGenerator instance cg,
    you need to write:
    
    cg.param_ranges['x'] = range(1,6,2) 
    """
    
    def __init__(self, config):
        """
        Constructor initialized with a given config.
        
        The given config sets default values for all parameters, that won't be
        changed by the ConfigGenerator.
        """
        self.config = config
        self.param_ranges = {}
    
    def getConfigurations(self):
        """
        Generates each possible parameter combination.
        
        According to the param_ranges given, all possible parameter 
        configurations are generated. 
        
        Returns a generator object, which can be used like an iterator.
        """
        config = self.config
        if len(list(self.param_ranges.items())) == 0:
            print("no ranges selected, return one configuration")
            yield config
        else:    
            #we need to make sure that key and value at index n belong together
            keys, values = list(zip(*list(self.param_ranges.items())))
            #cartesian product of all value ranges
            prod = itertools.product(*values)
            for params in prod:
                changedParams = dict(list(zip(keys, params)))
                for key, param in list(changedParams.items()):
                    config[key] = param
                yield config

                

class JanusConfig(Config):
    '''Config parameters for Janus to be used with the airwriting scripts'''
    
    janusCfgFileParams = ['dbdir', 'dbname', 'datadir', 'featdesc', 'feataccess',
                          'vocab', 'dict', 'feature', 'phones', 'trainset', 
                          'testset', 'devset', 'meansub', 'windowsize', 
                          'frameshift', 'wordPen', 'wordBeam', 'stateBeam',
                          'morphBeam', 'lz', 'hmmstates', 'hmm_repos_states',
                          'gmm', 'gmm_repos', 'iterations', 'channels',
                          'filter', 'transcriptkey', 'trainSet', 'devSet',
                          'testSet']
    
    modelFileKeys = ['codebookSetFile', 'codebookWeightsFile','distribSetFile',
                     'distribWeightsFile', 'topologiesFile', 'topologyTreeFile', 
                     'distribTreeFile', 'phonesSetFile', 'transitionModelsFile']
    
    def areModelFilesSet(self):
        print("modelFileKeys:")
        print((JanusConfig.modelFileKeys))
        print("self.keys:")
        print((list(self.keys())))
        ret = set(JanusConfig.modelFileKeys).issubset(list(self.keys()))
        print(("is subset: " + str(ret)))
        return(ret)
    
    def copyModelFilesToDst(self, dstDir):
        '''Copy the model files referenced in config to destination directory'''
        
        for fileKey in JanusConfig.modelFileKeys:
            if fileKey == 'distribWeightsFile' :
                shutil.copy(self[fileKey], os.path.join(dstDir, "distribWeights"))
            if fileKey == 'codebookWeightsFile':
                shutil.copy(self[fileKey], os.path.join(dstDir, "codebookWeights"))
            else:
                shutil.copy(self[fileKey], dstDir)
        #create dumm tags file
        f = open(os.path.join(dstDir, "tags"), "w")
        f.close()
        
    
    def writeLocalConfig(self, dirname):
        '''fill a directory with everything needed to run Janus Eval in it.
        
        In the directory given by dirname, the file rec.conf.tcl is created 
        and all relevant model files are copied. The directory must already 
        exist
        '''
        
        if self.areModelFilesSet():
            print("model files are set, copy to destination...")
            self.copyModelFilesToDst(dirname)
        
            #exctract some information from model files
            #assume all characters have the same number of gaussians
            #gcs = BioKIT.GaussianContainerSet()
            #gcs.readDescFile(self['codebookSetFile'])
            #self['gmm'] = gcs.getGaussianContainer("a-z0").getGaussiansCount()
            # = gcs.getGaussianContainer("a-z0").getDimensionality()
            #self['gmm_repos'] = gcs.getGaussianContainer("_-z0").getGaussiansCount()
            #find out topology
            #names = gcs.getGaussianContainerList()
            #modelNames = [x[0] for x in names]
            #self['hmmstates'] = modelNames.count("a")
            #self['hmm_repos_states'] = modelNames.count("_")
        
        
        #compose output string          
        s = ""
        s += "set conf {\n"
        for key in self.janusCfgFileParams:
            if key in list(self.keys()): #no key is mandatory
                if key == "channels":
                    s += key + " " + str(self[key]) + "\n"
                elif key == "filter":
                    s += key + " " + str(self[key]) + "\n"
                elif key in ["trainSet", "devSet", "testSet"]:
                    airUtil.writeSetFile(self[key], os.path.join(dirname, key))
                elif type(self[key]) != type(""):
                    s += key + " " + str(self[key]) + "\n"
                else:
                    s += key + " \"" + str(self[key]) + "\"\n"
            
        if self['LMType'] == "ngram":
            s += "ngram \"" + self['tokenSequenceModelFile'] + "\"\n"
        elif self['LMType'] == "grammar":
            s += "grammar \"" + self['tokenSequenceModelFile'] + "\"\n"
        else:
            raise RuntimeError("Unknown janusLMType: " + str(self.janusLMType) +
                               "should be one of {ngram,grammar}")
        s += "dirname " + dirname + "\n"
        s += "}\n"
        #actually write config file
        with open(os.path.join(dirname, "rec.conf.tcl"), "w") as f:
            f.write(s)
        #write serialization of self
        self.saveFile(os.path.join(dirname, "janusConfig.pickle"))
        self.saveTxtFile(os.path.join(dirname, "janusConfig.txt"))
   
     

class AirwritingConfig(Config):

    def writeLocalConfig(self, dirname, prefix = "bioKitLocalConf"):
        self.saveTxtFile(os.path.join(dirname, prefix + ".txt"))
        self.saveFile(os.path.join(dirname, prefix + ".pickle"))

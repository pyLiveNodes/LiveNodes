import BioKIT

import random
import itertools

class CrossValidation:
    """
    Generate training and test sets for n-fold cross validation
    
    The class encapsulates the process of generating the training and test sets
    for each fold when performing a cross validation. It operates on a given 
    table of a database and can subsequently produce and return the individual
    cross validation folds.  
    """
    
    def __init__(self, database, seed = None):
        """Constructs a cross validation instance
        
        Keyword arguments:
        database - a database object (open or close) with the tables to 
                   operate on.
        seed - seed to initialize the random number generator. For equal seeds,
            the data sets returned by this class are equal. The default value
            None means the actual elements of the created data sets are 
            indeterministic.
        """
        random.seed(seed)
        self.db = database
        if not database.isOpen():
            self.db.open()

    def getPerKeyCrossValidationFolds(self, key, table, slice_size = None):
        """
        Return a generator for the folds of a per key cross-validation.
        
        Generates folds of a cross validation from a database table where each
        fold contains only elements with equal values for the given key.
        For example typical keys would be a session or person id to perform per
        session or per person cross-validations. Each fold has the same size 
        and elements are selected randomly from all possible elements.
        
        Keyword arguments:
        key - the key as string, must correspond with the name of one column in
            the database
        table - the table to operate on, must exist
        slice_size - size of each fold, defaults to None, which means the largest
            possible slice_size is computed from data and used. The largest 
            slice_size equals the minimum over the size of the set of entries 
            for each key.
            
        Returns a generator that returns a dictionary with the entries testSet
            and trainSet, each containing a list of elements and keyval
            containing the value of the key for the given fold
        
        Raises Exception if number of data entries for at least one fold is 
            smaller than slice_size.
        """
        self.currentSetIndex = 0
        
        #get all possible values of key
        sqlcmd = "SELECT DISTINCT " + key + " FROM " + table
        self.db.logsql(sqlcmd)
        distinctkeys = [x[key] for x in self.db.executeStatement(sqlcmd)]
        #self.db.logres(distinctkeys)
        
        #find out minimum of size of all possible folds
        sqlcmd = ("SELECT " + key + ", min(totals) AS minTotal FROM " +
                  "( SELECT " + key + ", " + "count(*) AS totals FROM " + 
                  table + " GROUP BY " + key + ")")
        resIter = iter(self.db.executeStatement(sqlcmd))
        resDict = next(resIter)
        min_value = resDict[key]
        min_size = resDict['minTotal']
        if slice_size == None:
            slice_size = min_size
        #sanity check if the required number of entries per fold is present
        if min_size < slice_size:
            raise Exception("For " + key + "=" + min_value + " only " +
                                str(min_size) + " entries in table, but " +
                                "slice size of " + str(slice_size) +
                                 " requested") 
        #generate all folds
        folds = {}
        for keyval in distinctkeys:
            sqlcmd = ("SELECT * FROM " + table + " WHERE " + key + " = '"
                      + keyval + "'")
            result = self.db.executeStatement(sqlcmd)
            folds[keyval] = random.sample(result, slice_size)
            #cvSequences.append(folds[])
        #subsequently return each pair of test and train set
        nrfolds = len(folds)
        for keyval, fold in list(folds.items()):
            testSet = fold
            trainSet2d = [x for x in list(folds.values()) if x != testSet]
            trainSet = list(itertools.chain.from_iterable(trainSet2d))
            yield({'keyval': keyval, 'trainSet' : trainSet,
                   'testSet' : testSet, 'nrfolds': nrfolds})    
        
    def getNFoldCrossValidation(self, table, folds):
        '''
        Return a generator for the folds of a n-fold cross-validation.
        
        Generate the folds for a n-fold cross-validation from the entries of a
        the given table. The elements of the folds are randomly selected from
        the dataset. If the number of folds is not a divider of the size of
        the dataset, the resulting folds will not have equal size. In this 
        case, a warning message will be printed.
        
        arguments:
        table - the table containing the data
        folds - number of folds to produce
         
        '''
        sqlcmd = "SELECT * FROM " + table
        self.db.logsql(sqlcmd)
        result = self.db.executeStatement(sqlcmd)
        reslist = [i for i in result]
        random.shuffle(reslist)
        if len(reslist) % folds != 0:
            print(("getNFoldCrossValidation: Number of folds is not a divider ",
                "of entries in table. Folds will not all have equal size."))
        foldNr = 0
        for foldNr in range(folds):
            #for each foldNr, compute the residue of foldNr modulo folds
            testset = [x for x in enumerate(reslist) if (x[0]) % folds == foldNr]
            #and compute all residues except foldNr modulo folds
            trainset = [x for x in enumerate(reslist) if (x[0]) % folds != foldNr]
            yield({'trainSet' : trainset, 'testSet' : testset, 'number' : foldNr})

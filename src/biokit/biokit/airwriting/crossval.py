import random
import itertools
from sqlalchemy import func

class CrossValidation:
    """
    Generate training and test sets for n-fold cross validation
    
    The class encapsulates the process of generating the training and test sets
    for each fold when performing a cross validation. It operates on a given 
    table of a database and can subsequently produce and return the individual
    cross validation folds.  
    """
    
    def __init__(self, session, seed = None):
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
        self.session = session
        
    def getPerKeyCrossValidationFolds(self, key, subquery, slice_size = None):
        """
        Return a generator for the folds of a per key cross-validation.
        
        Generates folds of a cross validation from a database table where each
        fold contains only elements with equal values for the given key.
        For example typical keys would be a session or person id to perform per
        session or per person cross-validations. Each fold has the same size 
        and elements are selected randomly from all possible elements.
        
        subqueries can easily be constructed by adding .subquery() to the end
        of a regular query command.
        
        Keyword arguments:
        key - the name of the column as string, must correspond with the name
             of one column in the subquery object
        subquery - a sqlalchemy object returned by query.subquery()
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
        keys = self.session.query(subquery.c.get(key).label('key')).\
                        group_by(subquery.c.get(key)).all()
        keys = [x[0] for x in keys]
        print(("Found the following keys: %s" % (keys,)))
        
        stats = self.session.query(subquery.c.get(key).label('key'),
                              func.count(subquery.c.get(key)).label('count')).\
                        group_by(subquery.c.get(key)).subquery()
        row_min =  self.session.query(func.min(stats.c.count).label('minimum'),
                                 stats.c.key).one()
        min_value = row_min.key
        min_size = row_min.minimum
              
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
        for keyval in keys:
            print(("Generating fold for key value %s" % (keyval,)))
            rows = self.session.query(subquery).filter(subquery.c.get(key) == keyval).all()
            folds[keyval] = random.sample(rows, slice_size)
            
        #subsequently return each pair of test and train set
        nrfolds = len(folds)
        for keyval, fold in list(folds.items()):
            testSet = fold
            trainSet2d = [x for x in list(folds.values()) if x != testSet]
            trainSet = list(itertools.chain.from_iterable(trainSet2d))
            yield({'keyval': keyval, 'trainSet' : trainSet,
                   'testSet' : testSet, 'nrfolds': nrfolds})    
        
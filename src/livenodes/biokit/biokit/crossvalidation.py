import random


class CrossValidation:
    """
    Devides a dataset given through a simple Python-List into Training and
    Testset, using crossvalidation.
    
    Can both handle lists with or without a specific key-Column (e.g. used in
    Person-Independend or Person-Dependend training). 
    """

    def __init__(self, seed=1234):
        """
        Keyword arguments:
        
        seed - seed to initialize the random number generator. For equal seeds,
            the data sets returned by this class are equal. The default value
            None means the actual elements of the created data sets are 
            indeterministic.        
        """
        print(("CrossValidation: initialize with seed %s" % seed))
        random.seed(seed)
        self.classes = []
        self.keys = []
        self.classColumn = None

    def cutListToMinimum(self, list, min_val=None):
        """
        Reduces the number of samples per class to the minimum over all classes.

        Ensures, that every class has the same amount samples

        Arguments
        list - list with samples and labels (label is given as element
            defined by self.classColumn
        min_val - number of samples per class, if not given the minimum is
            taken as in the description above

        Returns a copy of the input list, in which each class has the same
        amount of samples, either the minimum or the number given by min_val
        """
        returnlist = [[item for item in list if item[self.classColumn] == x]
                      for x in self.classes]
        minimum = min([len(returnlist[x]) for x in self.classCount])
        if min_val is not None and min_val < minimum:
            minimum = min_val
        print(("CrossValidation: number of samples per class is %s" % minimum))
        returnlist = [
            random.sample(returnlist[x], minimum) for x in self.classCount
        ]
        return returnlist

    def createKFoldCrossvalidation(self,
                                   inputList,
                                   classColumn,
                                   K=None,
                                   maxsamples=None):
        """
        Performs k-fold-Crossvalidation on the given Dataset. A Generator for the
        different folds is returned.
        
        If a class column is specified, makes sure that the samples are uniformly
        distributed over all different classes found in that column. The same
        amount of samples are selected ramdomly for all classes, depending on
        the class with least samples given.  
        
        Keyword arguments:
        inputList - the Dataset, which has to be devided into folds
        classColumn - the column, which specifies the class of the given sample.
                        insert negative numbers, if classes should be ignored
        K - the number of folds, the dataset is devided into.
        maxsamples - limit the number of samples per class to the given value
        
        Return:
        A Generator for the different folds in form of a dictionary is returned.
        The dictionary has the entries "train" and "test", each giving a sublist of
        the original list.
        """
        #do we have a class column?
        print(("CrossValidation: create generator for %s folds" % K))
        if len(inputList) < K:
            raise ValueError(("CrossValidation: %s folds specified but only " +
                              "%s data points given") % (K, len(inputList)))
        if (classColumn >= 0):
            self.classColumn = classColumn
            self.classes = list(
                set([element[classColumn] for element in inputList]))
            print(("CrossValidation: found %s classes" % len(self.classes)))
            self.classCount = list(range(len(self.classes)))
            final = self.cutListToMinimum(inputList, min_val=maxsamples)
            if (K == None):
                K = len(final[0])
            for k in range(K):
                training = [[
                    value for i, value in enumerate(final[subClass])
                    if i % K != k
                ] for subClass in self.classCount]
                training = [item for sublist in training for item in sublist]
                validation = [[
                    value for i, value in enumerate(final[subClass])
                    if i % K == k
                ] for subClass in self.classCount]
                validation = [
                    item for sublist in validation for item in sublist
                ]
                yield ({'train': training, 'test': validation})

        else:
            if (K == None):
                K = len(inputList)
                print(("creating %s folds" % K))
            for k in range(K):
                training = [
                    value for i, value in enumerate(inputList) if i % K != k
                ]
                validation = [
                    value for i, value in enumerate(inputList) if i % K == k
                ]
                yield ({'train': training, 'test': validation})

    def createPerKeyCrossvalidation(self,
                                    inputList,
                                    keyColumn,
                                    classColumn=-1):
        """
        Performs per-key-Crossvalidation on the given Dataset. A Generator for the
        different folds is returned. Each fold only contains items with equal keys.
        
        If a class column is specified, makes sure that the samples are uniformly
        distributed over all different classes found in that column. The same
        amount of samples are selected ramdomly for all classes, depending on
        the class with least samples given and for every key either, depending
        on the key with least samples given.
        
        Keyword arguments:
        inputList - the Dataset, which has to be devided into folds
        keyColumn - the column, which specifies the key the sample belongs to.
            each fold contains only values with equal keys in the given column.
        classColumn - the column, which specifies the class of the given sample.
                        insert negative numbers, if classes should be ignored
        
        Return:
        A Generator for the different folds in form of a dictionary is returned.
        The dictionary has the entries "train" and "test", each giving a sublist of
        the original list. The entry "keyValue" comprised the key of the given fold,
        the entry "keyCount" gives the amount of keys found in the inputList
        """

        self.keys = list(set([element[keyColumn] for element in inputList]))
        keyCount = list(range(len(self.keys)))
        listPerKey = [[item for item in inputList if item[keyColumn] == x]
                      for x in self.keys]
        #do we have a class column?
        if (classColumn >= 0):
            self.classColumn = classColumn
            self.classes = list(
                set([element[classColumn] for element in inputList]))
            self.classCount = list(range(len(self.classes)))

            absoluteMinimum = min(
                [len(self.cutListToMinimum(x)[0]) for x in listPerKey])

            final = [
                self.cutListToMinimum(listPerKey[x], absoluteMinimum)
                for x in keyCount
            ]
            for i in keyCount:
                training = final[:i] + final[i + 1:]
                training = [item for sublist in training for item in sublist]
                training = [item for sublist in training for item in sublist]
                validation = [item for sublist in final[i] for item in sublist]
                yield ({
                    'train': training,
                    'test': validation,
                    'keyValue': validation[0][keyColumn],
                    'keyCount': len(keyCount)
                })
        else:
            minLen = min([len(listPerKey[x]) for x in keyCount])
            final = [random.sample(listPerKey[x], minLen) for x in keyCount]
            for i in keyCount:
                training = final[:i] + final[i + 1:]
                training = [item for sublist in training for item in sublist]
                validation = final[i]
                yield ({
                    'train': training,
                    'test': validation,
                    'keyValue': validation[0][keyColumn],
                    'keyCount': len(keyCount)
                })

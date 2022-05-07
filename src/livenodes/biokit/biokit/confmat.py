import numpy as np


class ConfusionMatrix:
    """
    Store result data and build confusion matrix from it
    """

    def __init__(self):
        self.data = {}

    def addResultList(self,
                      resultlist,
                      refkey="reference",
                      hypkey="hypothesis"):
        """
        Add a list of results as provided by the recognizer class.

        The result list must be a list of dictionariers, each providing the
        reference (or label) by the given refkey parameter and the hypothesis
        by the given hypkey parameter.
        """
        for r in resultlist:
            self.addResult(r[refkey], r[hypkey])

    def addResult(self, reference, hypothesis):
        """
        Add one reference-hypothesis pair to the class data
        
        Keyword arguments:
        reference -- string label of the reference
        hypothesis -- string label of the hypothesis
        """
        if reference in self.data:
            if hypothesis in self.data[reference]:
                self.data[reference][hypothesis] += 1
            else:
                self.data[reference][hypothesis] = 1
        else:
            self.data[reference] = dict({hypothesis: 1})

    def getMatrix(self):
        """
        Return confusion matrix as dictionary of dictionaries.
        """
        return self.data

    def getArray(self):
        """
        Return confusion matrix as numpy array
        :return: matrix as array and list of ordered references
        """
        references = sorted(self.data.keys())
        print(references)
        arr = np.zeros((len(references), len(references)), dtype=np.int)
        for ridx, ref in enumerate(references):
            for hidx, hyp in enumerate(references):
                if hyp in self.data[ref]:
                    arr[ridx, hidx] = self.data[ref][hyp]
        return arr, references

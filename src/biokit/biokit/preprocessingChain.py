# This class allows to chain function calls where the return value of an 
# operator is the first argument of the next operator
class PreprocessingChain:

    def __init__(self):
        self.__operators=[]
        self.__arguments=[]

    # Adds an operator function (including its arguments) to the preprocessing chain
    # @param operatorFunction Function pointer to the function to be executed in the chain
    # @param args Variable number of arguments
    def addOperator(self, operatorFunction, *args): 
        self.__operators.append(operatorFunction)
        self.__arguments.append(args)

    # Execute the previously added chain of pre-processing functions.
    # Each return value of an operator function is the first argument of the next operator funciton
    # The return value of the last operator function is returned
    # @param initialValue Value of the first argument of the first operator function in the chain
    # @param replacementDict Parameters in the form keyName=value that are translated to a python dict (by **)   
    def execute(self, initialValue, **replacementDict):
        ret = initialValue
        for operatorNr in range(0, len(self.__operators)):
            args = self.__arguments[operatorNr]
            #print "RepDict", replacementDict
            #print "args before replacement", args
            #replace entry of argument list with values from replacement dict
            args = [replacementDict[x] if x in replacementDict else x for x in args]
            #print "args after replacement", args
            ret = self.__operators[operatorNr](ret, *args)
        return ret
        

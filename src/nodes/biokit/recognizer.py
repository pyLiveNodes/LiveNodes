"""Recognizer: Convenience class to interact with BioKIT."""
import os
import tempfile
from enum import Enum
from collections import defaultdict

from . import BioKIT

# python-lib
from . import align
from . import logger
from .wkm import wkmb
from .wkm import wkmb2

import numpy as np
np.random.seed(1234)

class NoViterbiPath(Exception):
    """Exception when search does not result in a valid path."""
    def __init__(self, desc):
        self.desc = desc
    def __str__(self):
        return repr(self.desc)

class NoClustererInitialized(Exception):
    """Exception when clustering is called without an initialized clusterer."""
    def __init__(self, desc):
        self.desc = desc
    def __str__(self):
        return repr(self.desc)

class NoTrainerInitialized(Exception):
    """Exception when training without an initialized trainer."""
    def __init__(self, desc):
        self.desc = desc
    def __str__(self):
        return repr(self.desc)

class TrainerType(Enum):
    GmmTrainer = "gmm_trainer"
    MergeAndSplitTrainer = "merge_and_split_trainer"

class Recognizer(object):
    """
    Convenience class to build an HMM based classification/recognition system.

    The class handles model construction, initialization, training and testing.

    For the non-expert user: With this class, you can easily build a HMM based
    classifier, in which each class is represented as one HMM. You can
    currently only use left-to-right HMM topologies but you can define the
    number of states per class. The factory method createCompletelyNew creates
    a new recognizer with a minimum of parameters.

    For the expert user: This class implements rapid building of a context-free
    recognizer using k-means initialization, EM training of GMMs and decoding.
    Initialization, training and decoding can be done on atom or token level.
    The classes are given equal prior probabilities by default, however a
    sequence model (e.g. tokensequence model) can be given.

    Attributes:
        dictionary (BioKIT.Dictionary): describing the composition of
            tokens into atoms
        gaussianContainerSet (BioKIT.GaussianContainerSet)
        gaussMixturesSet (BioKIT.GaussMixturesSet)
        modelMapper (BioKIT.ModelMapper)
        atomMap (BioKIT.AtomManager)
        mixtureTree (BioKIT.MixtureTree)
        topologyInfo (BioKIT.TopologyInfo)
        vocabulary (BioKIT.SearchVocabulary
        tokenSequenceModel (BioKIT.AbstractTokenSequenceModel)
        gmmScorer (BioKIT.GmmFeatureVectorScorer)
        trainer (BioKIT.GmmTrainer)
        clusterer (BioKIT.ContextClusterer)
        samples (dict): container for data for init / training

    """

    HYPOBEAM = 700
    HYPOTOPN = 7000
    FINALHYPOBEAM = 500
    FINALHYPOTOPN = 1000
    LATTICEBEAM = 50


    def __init__(self, gaussianContainerSet, gaussMixturesSet, atomMap,
                 mixtureTree, topologyInfo, dictionary,
                 contextModel, vocabulary=None, initSearchGraph=True):
        """
        Create a new Recognizer with the given BioKIT-classes.

        Args:
            gaussianContainerSet (BioKIT.GaussianContainerSet)
            gaussMixturesSet (BioKIT.GaussMixturesSet)
            atomMap (BioKIT.AtomManager)
            mixtureTree (BioKIT.MixtureTree)
            topologyInfo (BioKIT.TopologyInfo)
            dictionary (BioKIT.Dictionary)
            contextModel (BioKIT.AbstractTokenSequenceModel)
            vocabulary (BioKIT.SearchVocabulary)
            initSearchGraph (bool): If True, set up the decoding search graph (not necessary for training) right now.
                The search graph can be initialized by calling initSearchGraph() later.
        """
        self.gaussianContainerSet = gaussianContainerSet
        self.gaussMixturesSet = gaussMixturesSet
        self.atomMap = atomMap
        self.mixtureTree = mixtureTree
        self.modelMapper = None
        self.topologyInfo = topologyInfo
        self.dictionary = dictionary
        self.decodingResultList = []
        self.rankList = []
        self.samples = defaultdict(list) # makes default for unknown keys [] instead of None, important in storeSamplesForInit
        self.atomsamples = {}
        self.trainer = None
        self.trainerType = TrainerType.GmmTrainer
        self.clusterer = None
        if vocabulary is None:
            self.vocabulary = BioKIT.SearchVocabulary(self.dictionary)
        else:
            self.vocabulary = vocabulary
        self.tokenSequenceModel = contextModel
        self.setSensibleValues()
        if initSearchGraph:
            self.initSearchGraph()
        self.decodecount = 0
        self.traincount = 0
        self._errorblame = False
        self.blamepath = None
        self.confusionHandler = None

    def setSensibleValues(self):
        """
        Set some sensible initial values for search parameters.

        Set sensible initial values for the following parameters that usually
        require additional tuning for optimal performance:

            - The Beams for Decoding
            - The Beams for Training
            - Token Sequence Model Weight
            - Token Insertion Penalty

        The values for the beam parameters are chosen rather high to favor
        accuracy at the expense of performance.
        """
        SEQUENCEMODELWEIGHT = 5
        TOKENINSERTIONPENALTY = 0

        self.beams = BioKIT.Beams(self.HYPOBEAM, self.HYPOTOPN,
                                   self.FINALHYPOBEAM, self.FINALHYPOTOPN,
                                   self.LATTICEBEAM)

        self.setTrainingBeams(self.HYPOBEAM, self.HYPOTOPN,
                                   self.FINALHYPOBEAM, self.FINALHYPOTOPN,
                                   self.LATTICEBEAM)

        self.sequenceModelWeight = SEQUENCEMODELWEIGHT
        self.tokenInsertionPenalty = TOKENINSERTIONPENALTY
        self.trainingTokenSequenceModelWeight = SEQUENCEMODELWEIGHT
        self.trainingTokenInsertionPenalty = TOKENINSERTIONPENALTY

    def initSearchGraph(self, tokenSequenceModel = None):
        """
        Initialize the search graph.

        Args:
            tokenSequenceModel (BioKIT.AbstractTokenSequenceModel): if not None,
                this token sequence model is used instead of the one already
                saved in the Recognizer.
        """
        self.gmmScorer = BioKIT.GmmFeatureVectorScorer(self.gaussMixturesSet)
        self.modelMapper = BioKIT.ModelMapper(self.topologyInfo,
                                              self.mixtureTree,
                                              self.atomMap)

        self.cacheScorer = BioKIT.CacheFeatureVectorScorer(self.gmmScorer)

        sequenceModel = self.tokenSequenceModel
        if tokenSequenceModel:
            sequenceModel = tokenSequenceModel

        self.handler = BioKIT.SearchGraphHandler(sequenceModel,
                                                 self.dictionary,
                                                 self.vocabulary,
                                                 self.modelMapper,
                                                 self.cacheScorer,
                                                 self.beams,
                                                 self.sequenceModelWeight,
                                                 self.tokenInsertionPenalty)
        self.decoder = BioKIT.Decoder(self.handler)

    def createSequenceModelLookAhead(self, maxLookAheadTreeDepth,
                                     lookAheadSequenceModelWeight,
                                     lookAheadCacheSize):
        """
        Add token sequence model lookahead to the search graph.

        Args:
            maxLookAheadTreeDepth (int): maximum depth of the search tree (may be -1 for no threshold)
            lookAheadSequenceModelWeight (float): Token sequence model weight to be used during lookahead
            lookAheadCacheSize (int): Size of the lookahead cache
        """
        if self.handler is None:
            raise ValueError("The search graph needs to be initialized first.")

        self.handler.createTsmLookAhead(maxLookAheadTreeDepth)
        self.handler.getTsmLookAhead().config().setTsmWeight(lookAheadSequenceModelWeight)
        self.handler.getTsmLookAhead().config().setMaxNodeCache(lookAheadCacheSize)

    def setTrainingBeams(self, hypoBeam, hypoTopN,
                         finalHypoBeam, finalHypoTopN, latticeBeam):
        """
        Set the beams used in training.

        Args:
            hypoBeam (float): Ensures that each Hypo's score is less or equal
                to the global best hypo's score plus hypo beam.
            hypoTopN (int): Ensures that only the N best Hypos will be propagated.
            finalHypoBeam (float): Ensures that the score of a Hypo in a word's
                final node is less or equal to the global best hypo's score plus
                final hypo beam.
            finalHypoTopN (int): Ensures that only the N best Hypos will be
                propagated for Hypos in a word's final node.
            latticeBeam (int): Every few decoding steps the Hypos on paths in
                the search network are pruned, unless the path's score is less or
                equal to the global best path's score plus lattice beam.
        """
        self.trainingBeams = BioKIT.Beams(hypoBeam, hypoTopN,
                                           finalHypoBeam, finalHypoTopN,
                                           latticeBeam)

    def limitSearchGraph(self, tokenlist):
        """
        Dynamically limit the Search Graph to only include the given tokens.

        Effectively, this limits the vocabulary during decoding.

        Args:
            tokenlist (list of str): list of token names to include in the vocabulary
        """
        self.gmmScorer = BioKIT.GmmFeatureVectorScorer(self.gaussMixturesSet)
        self.modelMapper = BioKIT.ModelMapper(self.topologyInfo,
                                              self.mixtureTree,
                                              self.atomMap)

        tokenids = []
        for token in tokenlist:
            id = self.dictionary.getTokenIds(token)
            tokenids += id
        vocabulary = BioKIT.SearchVocabulary(tokenids,
                                             self.dictionary)

        self.handler = BioKIT.SearchGraphHandler(self.tokenSequenceModel,
                                                 self.dictionary,
                                                 vocabulary,
                                                 self.modelMapper,
                                                 self.gmmScorer,
                                                 self.beams,
                                                 self.sequenceModelWeight,
                                                 self.tokenInsertionPenalty)
        self.decoder = BioKIT.Decoder(self.handler)

    def setBeams(self,hypoBeam, hypoTopN, finalHypoBeam, finalHypoTopN,
                 latticeBeam):
        """
        Set the beams used in decoding.

        New beams are set both for future search graphs and for the current
        search graph.

        Args:
            hypoBeam (float): Ensures that each Hypo's score is less or equal
                to the global best hypo's score plus hypo beam.
            hypoTopN (int): Ensures that only the N best Hypos will be propagated.
            finalHypoBeam (float): Ensures that the score of a Hypo in a word's
                final node is less or equal to the global best hypo's score plus
                final hypo beam.
            finalHypoTopN (int): Ensures that only the N best Hypos will be
                propagated for Hypos in a word's final node.
            latticeBeam (int): Every few decoding steps the Hypos on paths in
                the search network are pruned, unless the path's score is less or
                equal to the global best path's score plus lattice beam.
        """
        self.beams = BioKIT.Beams(hypoBeam, hypoTopN, finalHypoBeam,
                                  finalHypoTopN, latticeBeam)
        config = self.handler.getConfig()
        config.setHypoBeam(hypoBeam)
        config.setHypoTopN(hypoTopN)
        config.setFinalHypoBeam(finalHypoBeam)
        config.setFinalHypoTopN(finalHypoTopN)
        config.setLatticeBeam(latticeBeam)

    def setTokenInsertionPenalty(self, tokenInsertionPenalty):
        """
        Set the token insertion penalty for decoding.

        Args:
            tokenInsertionPenalty (float): penalty for the insertion of a new
                token during search
        """
        self.tokenInsertionPenalty = tokenInsertionPenalty
        self.handler.getConfig().setTokenInsertionPenalty(
            self.tokenInsertionPenalty)

    def setSequenceModelWeight(self, sequenceModelWeight):
        """
        Set the token sequence model weight for decoding.

        Args:
            sequenceModelWeight (float): weight of the token sequence model
        """
        self.sequenceModelWeight = sequenceModelWeight
        self.handler.getConfig().setTokenSequenceModelWeight(
            self.sequenceModelWeight)

    def setSearchResultHandler(self, searchResultHandler):
        """
        Set the SearchResultHandler of the recognizer.

        Args:
            searchResultHandler (BioKIT.AbstractSearchResultHandler):
                The new handler to be set
        """
        self.decoder.setSearchResultHandler(searchResultHandler)

    def setTrainerType(self, trainerType):
        """
        Set the trainer type to one of the types in recognizer.TrainerType.
        This will remove the current trainer and create a new trainer of
        the provided type.

        Args:
             trainerType (TrainerType): Type of trainer
        """
        if not isinstance(trainerType, TrainerType):
            raise ValueError("Received unknown type of trainer. Please use recognizer.TrainerType.")

        self.trainerType = trainerType

        if self.trainer is not None:
            self.trainer.clear()

        if self.trainerType is TrainerType.MergeAndSplitTrainer:
            self.trainer = BioKIT.MergeAndSplitTrainer(self.gaussMixturesSet)
        else:
            self.trainer = BioKIT.GmmTrainer(self.gaussMixturesSet)

    @classmethod
    def createCompletelyNew(cls, atomList, tokenDictionary, nrofmixtures,
                            featuredimensionality, sequenceRecognition=False,
                            tokenSequenceModel=None, initDecoding=True):
        """
        Create a completely new Recognizer.

        This is the method you want to use if you want to create a new
        recognizer with minimal effort. You only need to provide the
        list of atoms, a token dictionary containing the mapping from
        atoms to tokens, the number of components for the gaussian
        mixtures and the dimensionality of the feature space.

        Args:
            atomList (dict): containing the Atom names as keys and
                their HMM topology as a list of state names as values

                example:
                {"atom1" : ["0","1","2","3","4"],
                "atom2" : ["0","1","2","3"]}

            tokenDicitonary (dict): the mapping of tokens to atoms,
                token names are given as keys and atom names as list

                example (for the atom equals token case):
                { "run": ["run"],
                "jump": ["jump"], ...

                example (for the general case):
                { "hello": ["h", "e", "l", "l", "o"],
                "no": ["n", "o"] }

            nrofmixtures (int): the number of GMM components used
            featuredimensionality (int): the dimensionality of the feature space
            sequenceRecognition (bool): If set to False (Default), a classification
                is performed, ie. each given data sample is classified as
                exactly one of the given tokens. If set to True, each data sample
                is recognized as a sequence of tokens with a zero-gram
                tokenSequenceModel if not specified otherwise.
            tokenSequenceModel (BioKIT.AbstractTokenSequenceModel): Used if
                sequenceRecognition is set to True, ignored otherwise. If None,
                no token sequence model is used.
            initDecoding (bool): If True, the recognizer will be set up for decoding. This is not necessary for training
                a model. The recogizer can still be set up for decoding later by calling initSearchGraph().

        Returns:
            a plain new instance of the Recognizer class

        """
        # create AtomManager and Dictionary
        atomManager = BioKIT.AtomManager()
        for atom in sorted(atomList):
            atomManager.addAtom(atom, ["atoms"], True)

        dictionary = BioKIT.Dictionary(atomManager)
        for dictEntry in sorted(tokenDictionary):
            dictionary.addToken(dictEntry, tokenDictionary[dictEntry])

        num_atoms = len(atomList)
        num_dict_atoms = len(dictionary.getAtomManager())
        if num_atoms != num_dict_atoms:
            logger.warn("Mismatch between dictionary and atomList. dictionary: {} atoms, atomList: {} atoms".format(num_dict_atoms, num_atoms))

        # create hmms
        topologyInfo = BioKIT.TopologyInfo()
        topoTree = topologyInfo.getTopoTree()

        if type(nrofmixtures) == int:
            tmpdict = {}
            for atom in atomList:
                tmpdict[atom] = nrofmixtures
            nrofmixtures = tmpdict

        for atom in nrofmixtures:
            if type(nrofmixtures[atom]) == int:
                tmplist = len(atomList[atom]) * [nrofmixtures[atom], ]
                nrofmixtures[atom] = tmplist

        gaussianContainerSet = BioKIT.GaussianContainerSet()
        gaussMixturesSet = BioKIT.GaussMixturesSet(gaussianContainerSet)
        gmmScorer = BioKIT.GmmFeatureVectorScorer(gaussMixturesSet)
        mixtureTree = BioKIT.MixtureTree(gmmScorer)

        #create a new topology for every given token
        for atom in atomList:
            rootNodes = []
            transitions = []
            states = atomList[atom]
            #if the token only has 1 state, then there is only the outgoing
            #transition
            if(len(states) == 1):
                rootNodes = ['ROOT-' + states[0]]
                transitions = []
                initialStates = [0]
                transitions.append(BioKIT.Transition(0, 0, 0.7))
                outgoingTransitions = [(0, 0.7)]
                topologyInfo.addTopology(atom, rootNodes, transitions,
                                         initialStates, outgoingTransitions)
            #else every state (except the last one) points to itself
            #and the next state
            else:
                for index, name in enumerate(states):
                    rootNodes.append('ROOT-' + name)
                    transitions.append(BioKIT.Transition(index, index, 0.7))
                    if index != len(states) - 1:
                        transitions.append(
                            BioKIT.Transition(index, index + 1, 0.7))

            initialStates = [0]
            outgoingTransitions = [(len(states) - 1, 0.7)]
            topologyInfo.addTopology(atom, rootNodes, transitions,
                                     initialStates, outgoingTransitions)

        #add a simple decisiontree for the tokens
        if (len(atomList) == 1):
            tokenname = next(iter(atomList.keys()))
            rootNode = BioKIT.TopoTreeNode('ROOT')
            topoTree.addRootNode(rootNode)
            node = BioKIT.TopoTreeNode(tokenname, tokenname)
            rootNode.setChildNode(False, node)
            rootNode.setChildNode(True, node)
        else:
            i = 0
            newNode = BioKIT.TopoTreeNode('ROOT-' + str(i))
            topoTree.addRootNode(newNode)
            for atom in atomList:
                i = i + 1
                if (i <= len(atomList) - 1):
                    rootNode = newNode
                    rootNode.setQuestions('0=' + atom)
                    rootNode.setChildNode(True,
                                          BioKIT.TopoTreeNode(atom, atom))
                    newNode = BioKIT.TopoTreeNode('ROOT-' + str(i))
                    rootNode.setChildNode(False, newNode)
                else:
                    rootNode.setChildNode(False,
                                          BioKIT.TopoTreeNode(atom, atom))

        # now start adding tokens and atoms
        for atom in sorted(atomList):
            cls.addModel(atom, atomList[atom], nrofmixtures[atom],
                         featuredimensionality, gaussianContainerSet,
                         gaussMixturesSet, mixtureTree)

        #start and end tokens are necessary for the grammar
        if not sequenceRecognition:
            tsm = cls.buildTokenGrammar(dictionary)
        else:
            if tokenSequenceModel:
                tsm = tokenSequenceModel
            else:
                tsm = BioKIT.ZeroGram(dictionary)

        #create the Recognizer and return it
        return(cls(gaussianContainerSet,
                   gaussMixturesSet,
                   dictionary.getAtomManager(),
                   mixtureTree,
                   topologyInfo,
                   dictionary,
                   tsm,
                   initSearchGraph=initDecoding))

    @staticmethod
    def buildTokenGrammar(dictionary):
        """
        Create a grammar that allows only one token to be recognized at a time.

        Args:
            dictionary (BioKIT.Dictionary): Grammar is built for the tokens
                in this dictionary

        Returns:
            the grammar

        """
        logger.log(BioKIT.LogSeverityLevel.Information, "Creating grammar tokensequence model")
        dictionary.config().setStartToken("<S>")
        dictionary.config().setEndToken("<E>")
        vocabulary = BioKIT.SearchVocabulary(dictionary)

        grammar = BioKIT.GrammarTokenSequenceModel(dictionary)
        nt0 = grammar.addNonTerminalNode("nt0")
        #nt0_0 = grammar.setStartSymbol(nt0)
        grammar.setStartSymbol(nt0)
        allowedTokens = vocabulary.getVocabulary()
        for token in sorted(allowedTokens):
            logger.log(BioKIT.LogSeverityLevel.Debug, "creating terminal node for " + dictionary.getToken(token))
            nodeId = grammar.addTerminalNode(token)
            logger.log(BioKIT.LogSeverityLevel.Debug, "adding edge from " + str(nt0) + " to " + str(nodeId))
            grammar.addSuccessor(nt0, nodeId)
            logger.log(BioKIT.LogSeverityLevel.Debug, "set " + str(nodeId) + " as end node")
            grammar.setEndNode(nodeId)
        return(grammar)

    @staticmethod
    def addModel(atom, substates, nrOfGaussians, dim, gaussianContainerSet,
                 gaussMixturesSet, mixtureTree):
        """
        Add models for an atom.

        Args:
            atom (str): atom to be modelled
            substates (list of str): the HMM states for the atom
            nrOfGaussians (list of int): number of Gaussians for each state
            dim: dimensionality of the features to be modelled
            gaussianContainerSet: GaussianContainerSet to which the model is added
            gaussMixturesSet: GaussianMixtutesSet to which the model is added
            mixtureTree: MixtureTree to which the model is added
        """
        for idx, substate in enumerate(substates):
            # add model information to Gaussian Container Set
            modelName = atom + '-' + substate
            hookName = 'hook-' + modelName
            if not modelName in \
               gaussianContainerSet.getGaussianContainerList():
                gaussianContainerSet.addGaussianContainer(modelName,
                                                          nrOfGaussians[idx],
                                                          dim, "DIAGONAL")

            if not modelName in gaussMixturesSet.getAvailableModelIds():
                gaussMixturesSet.addGaussMixture(modelName, modelName)

            # make new nodes
            questionStr = '0=%s' % atom
            newHook = BioKIT.MixtureTreeNode(hookName)
            newLeaf = BioKIT.MixtureTreeNode(modelName, modelName)
            newDummyNode = BioKIT.MixtureTreeNode("-")

            # add model to mixture tree - first possibly create the root node,
            # then create the mode
            mixtureTreeRoots = mixtureTree.getRootNodes()
            if not 'ROOT-' + substate in mixtureTreeRoots:
                treeRoot = BioKIT.MixtureTreeNode('ROOT-' + substate)
                mixtureTree.addRootNode(treeRoot)
                treeRoot.setChildNode(True, newHook)
            else:
                treeRoot = mixtureTreeRoots['ROOT-' + substate]

            # descend along "no" path until a node without "no" child is found
            # that node is a dummy node.
            parentNode = treeRoot
            thisNode = treeRoot
            theseChildren = thisNode.getChildNodes()
            while False in theseChildren:
                # descend
                parentNode = thisNode
                thisNode = theseChildren[False]
                theseChildren = thisNode.getChildNodes()

            # now add new hook node and leaf node here
            # replacing the existing dummy
            parentNode.setChildNode(False, newHook)
            newHook.setQuestions(questionStr)
            newHook.setChildNode(True, newLeaf)
            newHook.setChildNode(False, newDummyNode)

    @classmethod
    def createNewFromLegacyFile(cls, path, sequencemodel=None,
                                sequenceRecognition=False, useFiller=False,
                                codebookSet="codebookSet",
                                codebookWeights="codebookWeights",
                                distribSet="distribSet",
                                distribWeights="distribWeights",
                                distribTree="distribTree",
                                phonesSet="phonesSet",
                                topologyTree="topologyTree",
                                topologies="topologies",
                                transitionModels="transitionModels",
                                dictfile="dictionary",
                                vocabfile=None
                                ):
        """
        Create a recognizer from files in legacy format.

        Args:
            path (str): Path of directory that contains the files
            sequencemodel (str): File path of N-gram token sequence model in arpa format.
                If None, no token sequence model is used.
            sequenceRecognition (bool): If set to False (Default), a classification
                is performed, ie. each given data sample is classified as
                exactly one of the given tokens. If set to True, each data sample
                is recognized as a sequence of tokens with a zero-gram
                tokenSequenceModel if not specified otherwise.
            useFiller (bool): Use a filler token, must be specified as FILLER in
                dictionary
            codebookSet (str): File name of the GaussianContainerSet desc
            codebookWeights (str): File name of the GaussianContainerSet data
            distribSet (str): File name of the GaussMixturesSet desc
            distribWeights (str): File name of the GaussMixturesSet data
            distribTree (str): File name of the MixtureTree
            phonesSet (str): File name of the set of atoms
            topologyTree (str): File name of the TopologyTree
            topologies (str): File name of the Topologies
            transitionModels (str): File name of the TransitionModel
            dictfile (str): File name of the Dictionary

        Returns:
            a new Recognizer, initialized with the given files

        """
        gaussianContainerSet = BioKIT.GaussianContainerSet()
        gaussianContainerSet.readDescFile(os.sep.join([path, codebookSet]))
        gaussianContainerSet.loadDataFile(os.sep.join([path, codebookWeights]))
        gaussMixturesSet = BioKIT.GaussMixturesSet(gaussianContainerSet)
        gaussMixturesSet.readDescFile(os.sep.join([path, distribSet]))
        gaussMixturesSet.loadDataFile(os.sep.join([path, distribWeights]))
        gmmScorer = BioKIT.GmmFeatureVectorScorer(gaussMixturesSet)

        atomMap = BioKIT.AtomManager()
        atomMap.readAtomManager(os.sep.join([path, phonesSet]))

        dictionary = BioKIT.Dictionary(atomMap)
        if useFiller:
            dictionary.registerAttributeHandler("FILLER",
                BioKIT.NumericValueHandler())
        dictionary.readDictionary(os.sep.join([path, dictfile]))
        if vocabfile is None:
            vocabulary = BioKIT.SearchVocabulary(dictionary)
        else:
            vocabulary = BioKIT.SearchVocabulary(os.sep.join([path, vocabfile]), dictionary)

        modelMapper = BioKIT.ModelMapper.ReadTopology(
            gmmScorer, atomMap, os.path.join(path,distribTree),
            os.path.join(path,topologyTree),
            os.path.join(path, topologies),
            os.path.join(path, transitionModels))
        mixtureTree = modelMapper.getMixtureTree()
        topologyInfo = modelMapper.getTopologyInfo()

        if sequencemodel is None:
            if not sequenceRecognition:
                tsm = cls.buildTokenGrammar(dictionary)
            else:
                tsm = BioKIT.ZeroGram(dictionary)
            if useFiller:
                tsm = BioKIT.FillerWrapper(tsm, dictionary, "FILLER")
        else:
            dictionary.config().setStartToken("<s>")
            dictionary.config().setEndToken("</s>")
            dictionary.config().setUnknownToken("<UNK>")
            ngram = BioKIT.NGram(dictionary)
            ngram.readArpaFile(sequencemodel, vocabulary)
            if useFiller:
                fillerWrapper = BioKIT.FillerWrapper(ngram, dictionary, "FILLER")
                cacheTsm = BioKIT.CacheTokenSequenceModel(fillerWrapper, dictionary)
                tsm = cacheTsm
            else:
                tsm = ngram
        return(cls(gaussianContainerSet, gaussMixturesSet, atomMap,
                   mixtureTree, topologyInfo, dictionary,
                   tsm, vocabulary))

    @classmethod
    def createNewFromFile(cls, path, contextmodel=None,
                          sequenceRecognition=False, useFiller=False):
        """
        Load an existing Recognizer from files.

        The following files must be present in the given directory:
        gaussianDesc
        gaussianData
        mixtureDesc
        mixtureData
        atomMap
        mixtureTree
        topologyTree
        topologies
        dictionary

        Args:
            path (str): Path of directory that contains the files
            contextmodel (str): File path of N-gram token sequence model in arpa format.
                If None, no token sequence model is used.
            sequenceRecognition (bool): If set to False (Default), a classification
                is performed, ie. each given data sample is classified as
                exactly one of the given tokens. If set to True, each data sample
                is recognized as a sequence of tokens with a zero-gram
                tokenSequenceModel if not specified otherwise.
            useFiller (bool): Use a filler token, must be specified as FILLER in
                dictionary

        Returns:
            a new Recognizer, initialized with the given files

        """
        logger.log(BioKIT.LogSeverityLevel.Information, "create recognizer from files in %s" % path)
        topologyInfo = BioKIT.TopologyInfo()
        gaussianContainerSet = BioKIT.GaussianContainerSet()
        gaussMixturesSet = BioKIT.GaussMixturesSet(gaussianContainerSet)
        gmmScorer = BioKIT.GmmFeatureVectorScorer(gaussMixturesSet)
        mixtureTree = BioKIT.MixtureTree(gmmScorer)
        atomMap = BioKIT.AtomManager()
        gaussianContainerSet.readDescFile(os.sep.join([path, 'gaussianDesc']))
        gaussianContainerSet.loadDataFile(os.sep.join([path, 'gaussianData']))
        gaussMixturesSet.readDescFile(os.sep.join([path, 'mixtureDesc']))
        gaussMixturesSet.loadDataFile(os.sep.join([path, 'mixtureData']))
        atomMap.readAtomManager(os.sep.join([path, 'atomMap']))
        mixtureTree.readTree(os.sep.join([path, 'mixtureTree']))
        topologyInfo.readTopologyTree(os.sep.join([path, 'topologyTree']))
        topologyInfo.readTopologies(os.sep.join([path, 'topologies']))
        dictionary = BioKIT.Dictionary(atomMap)
        if useFiller:
            dictionary.registerAttributeHandler("FILLER",
                BioKIT.NumericValueHandler())
        dictionary.readDictionary(os.sep.join([path, 'dictionary']))
        vocabulary = BioKIT.SearchVocabulary(dictionary)
        if contextmodel is None:
            if not sequenceRecognition:
                tsm = cls.buildTokenGrammar(dictionary)
            else:
                tsm = BioKIT.ZeroGram(dictionary)
        else:
            dictionary.config().setStartToken("<s>")
            dictionary.config().setEndToken("</s>")
            dictionary.config().setUnknownToken("<UNK>")
            ngram = BioKIT.NGram(dictionary)
            ngram.readArpaFile(contextmodel, vocabulary)
            if useFiller:
                fillerWrapper = BioKIT.FillerWrapper(ngram, dictionary, "FILLER")
                cacheTsm = BioKIT.CacheTokenSequenceModel(fillerWrapper, dictionary)
                tsm = cacheTsm
            else:
                tsm = ngram

        return(cls(gaussianContainerSet, gaussMixturesSet, atomMap,
                   mixtureTree, topologyInfo, dictionary,
                   tsm))

    def registerDictionaryAttributeHandler(self, attribute, handler=BioKIT.StringHandler()):
        """
        Register handler for attribute in the dictionary.

        Attributes are used in clustering, error blaming and wrapping fillers
        in the FillerWrapper token sequence models.

        Currently have two relevant types of attribute handlers:

        StringHandler:
        Example dictionary entry:
        fillerToken {fillerAtom} [FILLERATTR]

        registerDictionaryAttribute('FILLERATTR', StringHandler())

        NumericValueHandler:
        fillerToken {fillerAtom} [FILLERATTRPENALTY 0.3]

        registerDictionaryAttribute('FILLERATTRPENALTY', NumericValueHandler())

        Args:
            attribute (str): Name of the attribute in the dictionary
            handler (BioKIT.DictionaryAttributeHandler): Handler to use for the attribute
        """
        self.dictionary.registerAttributeHandler(attribute, handler)

    def addDictionaryAttribute(self, tokenOrTokenId, attribute, value):
        """
        Add an attribute to token in the dictionary.
        If token has more than one id (i.e. more than one representation),
        the attribute is added to all ids.

        A handler for this attribute must be added before calling this function.

        Args:
            tokenOrTokenId (str or int): token or token Id for which filler will be added
            attribute (str): Name of the attribute in the dictionary
            value (str or float): Value of the attribute. Must match the registered attribute handler.
        """

        if type(tokenOrTokenId) is int:
            tokenIds = [tokenOrTokenId]
        else:
            tokenIds = self.dictionary.getTokenIds(tokenOrTokenId)

        for tokenId in tokenIds:
            self.dictionary.addAttributeToToken(tokenId, attribute, value)

    def plotpath(self, fs, path):
        """
        Plot Viterbi path with generated feature sequence.

        Args:
            fs - the feature sequence that produced the path
            path (BioKIT.Path): the Viterbi path
        """
        import visualization as vis
        vis.plot_path_feat(path, self.handler, self.gmmScorer, fs)
        vis.show()

    def decode(self, fs, reference=None, generatepath=False, nbest=1, initialize=True, returnscores=False):
        """
        Decode a feature sequence.

        A Hypothesis for the given Feature Sequence is calculated by evaluating
        the best path using the Viterbi Algorithm.
        Hypothesis and reference of the given Sample are stored.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            reference (str): reference to the given sample if available
            generatepath (bool): if True, generate resulting viterbi path and return it
            nbest (int): retrieve the n-best hypothesis (default is only the one best)
            initialize (bool): initialize searchgraph before search. Pass False for incremental search
            returnscores (bool): return the search scores

        Returns:
            A tuple of resulting tokens and path and scores.
            If generatepath is False then the return value of path is None.
            If returnscores is False then the return value of scores is None.
            If nbest==1 then the result is given as string of the best hypothesis,
            or None if no hypothesis was found.
            If nbest>1 then the result is given as list of the the best hypothesis in
            ascending order (first element is the best hypothesis) or
            a list containing None, if no hypothesis was found.

        """
        mcfs = [fs]

        if self._errorblame:
            self.handler.setKeepHyposAlive(True)
            filename = "hyp.%s.snp" % self._blameid
            snapshotName = os.path.join(self._get_blamepath(), filename)
            self.handler.createSnapshot(snapshotName,
                                        self.sequenceModelWeight,
                                        self.tokenInsertionPenalty)

        self.decoder.search(mcfs, initialize)
        raw_results = self.decoder.extractSearchResult(nbest,
                                                   self.handler.getConfig().
                                                       getLatticeBeam(),
                                                   "FILLER")
        results = [r.toString().strip() for r in raw_results]

        if len(results) != 0:
            hypo = results[0]
        else:
            hypo = ""
        logger.log(BioKIT.LogSeverityLevel.Information, "HYPO: %s" % (hypo))
        logger.log(BioKIT.LogSeverityLevel.Information, "REF: %s" % (reference))
        
        if reference is not None:
            ter = align.tokenErrorRate(reference, hypo)
            logger.log(BioKIT.LogSeverityLevel.Information, "Token Error Rate: " + str(ter))

            # compute the rank of the correct hypothesis in the nbest list
            if nbest > 1:
                rankofcorrect = None
                for rank, res in enumerate(results):
                    logger.log(BioKIT.LogSeverityLevel.Information, "%s-best hypo: %s" % (rank+1, res))
                    if align.tokenErrorRate(reference, res) == 0.0:
                        rankofcorrect = rank+1
                        break
                logger.log(BioKIT.LogSeverityLevel.Information, "Rank of correct result: %s" % rank)
                self.rankList.append({'reference': reference, 'rank': rank})

            #save in result list for final TER computation
            self.decodingResultList.append({'reference': reference,
                                            'hypothesis': hypo})
        if nbest == 1:
            retval = hypo
        else:
            retval = results

        if returnscores:
            scores = [r.score for r in raw_results]
        else:
            scores = None

        if generatepath:
            try:
                path = self.decoder.traceViterbiPath()
            except RuntimeError:
                path = None
        else:
            path = None

        return (retval, path, scores)

    def getDecodingResult(self):
        """
        Get the results of the last decodings.

        Returns:
            list of dicts containing the hypothesis and the reference

        """
        return self.decodingResultList

    def getDecodingTER(self):
        """Calculate the token error rate of the current decoding."""
        return align.totalTokenErrorRate(self.decodingResultList)

    def getAtomManager(self):
        """Get the atom manager."""
        return self.atomMap

    def getDecoder(self):
        """Get the decoder."""
        return self.decoder

    def getDictionary(self):
        """Get the token dictionary."""
        return self.dictionary

    def getScorer(self):
        """Get the feature vector scorer."""
        return self.gmmScorer

    def getSearchGraph(self):
        """Get the search graph."""
        return self.handler.getSearchGraph()

    def getGaussMixturesSet(self):
        """Get the GaussMixturesSet of the scorer."""
        return self.gaussMixturesSet

    def _get_blamepath(self):
        if not self.blamepath:
            self.blamepath = tempfile.mkdtemp()
        return self.blamepath

    def storeSequenceForBlame(self, fs, listOfTokenNames, id, flexibility, hypos=None):
        """
        Perform error blaming for the given data sample.

        Args:
            fs (BioKIT.FeatureSequence): a sample feature sequence
            listOfTokenNames (list of str): Sequence of tokens in the feature sequence
            id: id of the feature sequence
            flexibility:

        """
        self._errorblame = True
        self._blameid = id
        self.forcedSequenceAlignment(fs, listOfTokenNames)
        self.decode(fs)
        #the snapshot files are now in self.blamepath/[ref|hyp].id.snp
        errorBlamer = BioKIT.ErrorBlamer(self.dictionary,
                                         flexibility,
                                         self.getScorer())
        hypsnapshot = os.path.join(self._get_blamepath(), "hyp.%s.snp" % id)
        refsnapshot = os.path.join(self._get_blamepath(), "ref.%s.snp" % id)
        #shrinksnapshot = os.path.join(self._get_blamepath(), "shrink.%s.snp" % id)
        #BioKIT.SnapshotHandler.Shrink(hypsnapshot, hypos, shrinksnapshot)
        logger.log(BioKIT.LogSeverityLevel.Information, "load snapshots")
        errorBlamer.loadSnapshots(hypsnapshot, refsnapshot)
        if not self.blamelogs:
            self.blamelogs = {}
        self.blamelogs[id] = errorBlamer.blameAndWriteUtterance()
        if not self.confusionHandler:
            self.confusionHandler = BioKIT.ConfusionHandler(self.getScorer())
        self.confusionHandler.collectConfusions(hypsnapshot, refsnapshot)

    def getBlameResults(self):
        """Return blame log and confusion mapping and reset error blaming."""
        confusion = self.confusionHandler.toCSV()
        blamelogs = self.blamelogs
        self.confusionHandler = None
        self.blamelogs = None
        return (blamelogs, confusion)

    def forcedAlignment(self, fs, tokenName):
        """
        Perform a forced viterbi alignment of a single token.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            tokenname (str): name of token, which is to be trained

        Returns:
            the viterbi path or None if no path was found.

        """
        return self.forcedSequenceAlignment(fs, [tokenName])

    def forcedSequenceAlignment(self, fs, listOfTokenNames, fillerOrFillerTokenId = -1,
                                doNotAllowOptionalFillersAndVariations = True,
                                addFillerToBeginningAndEnd = False):
        """
        Perform a forced viterbi alignment of a token sequence.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            listOfTokenNames (list of str): ordered list of token names, that are to be trained
            fillerOrFillerTokenId (str or int): Optional filler between tokens in the token sequence.
                Either as a token (str) or the id of the token in the dictionary.
            doNotAllowOptionalFillersAndVariations (bool) - If True only use the first atom
                            sequence matching the tokens in the token sequence and
                            do not allow optional filler between tokens
            addFillerToBeginningAndEnd (bool): if True, filler is added at beginning and end
                of the token sequence

        Returns:
            the viterbi path or None if no path was found.

        """
        if type(fillerOrFillerTokenId) is int:
            fillerTokenId = fillerOrFillerTokenId
        else:
            fillerTokenId = self.dictionary.getTokenIds(fillerOrFillerTokenId)[0]

        if addFillerToBeginningAndEnd:
            fillerToken = self.dictionary.getToken(fillerTokenId)
            listOfTokenNames[:0] = fillerToken
            listOfTokenNames.append(fillerToken)

        gmmScorer = BioKIT.GmmFeatureVectorScorer(self.gaussMixturesSet)
        cacheScorer = BioKIT.CacheFeatureVectorScorer(gmmScorer)

        modelMapper = BioKIT.ModelMapper(self.topologyInfo,
                                         self.mixtureTree,
                                         self.atomMap)

        mcfs = [fs]
        tokenIDs = []
        for tokenName in listOfTokenNames:
            tokenIds = self.dictionary.getTokenIds(tokenName)
            assert(len(tokenIds) == 1)
            tokenIDs.append(tokenIds[0])

        logger.log(BioKIT.LogSeverityLevel.Debug, "Forced Alignment for %s (token ids %s)" % (listOfTokenNames, tokenIDs))
        handler = BioKIT.SearchGraphHandler(
            self.dictionary, tokenIDs,
            fillerTokenId, doNotAllowOptionalFillersAndVariations, modelMapper,
            cacheScorer, self.trainingBeams,
            self.trainingTokenSequenceModelWeight,
            self.trainingTokenInsertionPenalty)

        decoder = BioKIT.Decoder(handler)

        if self._errorblame:
            filename = "ref.%s.snp" % self._blameid
            snapshotName = os.path.join(self._get_blamepath(), filename)
            handler.createSnapshot(snapshotName,
                                   self.sequenceModelWeight,
                                   self.tokenInsertionPenalty)

        decoder.search(mcfs, True)
        res = decoder.extractSearchResult()
        #logger.log(BioKIT.LogSeverityLevel.Information, "forcedalign result: %s" % res)
        # in case a snapshot was created, traceViterbiPath does not work
        # since the snapshot leads to an inconsistent state of hypos in the
        # search graph
        if self._errorblame:
            path = None
        else:
            path = decoder.traceViterbiPath()
        return path

    def storeTokenForTrain(self, fs, tokenName, fillerToken = "filler", ignoreNoPathException=False):
        """
        Add one token to the training iteration.

        This method must be called for every token in the training data
        set. The method computes a viterbi alignment of the given token
        with the feature sequence. The path is stored for later update
        of the GMMs.
        After calling this method for all tokens in the training set,
        you need to call finishTrainIteration to do the update.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            tokenName (str):- name of token, which is to be trained
            ignoreNoPathException (bool): if True, no exception is raised when no
                valid path could be found
            fillerToken (str): token to be used as filler

        Raises:
            NoViterbiPath: if no valid path could be found and
                ignoreNoPathException=False

        """
        self.storeTokenSequenceForTrain(fs, [tokenName], ignoreNoPathException, fillerToken)

    def storeTokenSequenceForTrain(self, fs, listOfTokenNames,
                                   ignoreNoPathException=False,
                                   fillerToken = "filler",
                                   addFillerToBeginningAndEnd = False):
        """
        Add a sequence of tokens to the training iteration.

        This method must be called for every token sequence in the training data
        set. The method computes a Viterbi alignment of the given tokens
        with the feature sequence. The path is stored for later update
        of the GMMs.
        After calling this method for all tokens sequences in the training set,
        you need to call finishTrainIteration to do the update.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            listOfTokenNames (list of str): ordered list of token names, that are to be trained
            ignoreNoPathException (bool): if True, no exception is raised when no
                valid path could be found
            fillerToken (str): token to be used as filler
            addFillerToBeginningAndEnd (bool): if True, filler is added at beginning and end
                of the token sequence

        Raises:
            NoViterbiPath: if no valid path could be found and
                ignoreNoPathException=False

        """
        self.traincount += 1
        if (self.trainer is None):
            if self.trainerType is TrainerType.MergeAndSplitTrainer:
                self.trainer = BioKIT.MergeAndSplitTrainer(self.gaussMixturesSet)
            else:
                self.trainer = BioKIT.GmmTrainer(self.gaussMixturesSet)

        try:
            path = self.forcedSequenceAlignment(fs, listOfTokenNames, fillerOrFillerTokenId=fillerToken, addFillerToBeginningAndEnd=addFillerToBeginningAndEnd)
            self.trainer.accuPath(fs, path, 1.0)
        except RuntimeError as e:
            if ignoreNoPathException:
                logger.log(BioKIT.LogSeverityLevel.Information, 'Ignoring error in forced alignment for %s,'
                                                                'error was: %s' % (listOfTokenNames, str(e)))
            else:
                logger.log(BioKIT.LogSeverityLevel.Information, "raise NoViterbiPath exception")
                raise NoViterbiPath(str(e))

    def storePathForTrain(self, fs, path):
        """
        Add a feature sequence with precomputed path to the training iteration.

        The the models used to create the given path must match the models in
        this recognizer object.

        Use case for this function is if the same model should be trained but
        with an increase in the number of Gaussians for each GMM. The process
        would involve several training iterations where the number of Gaussians
        in each GMM is increased gradually.

        This method must be called for every path in the training data
        set. The path is stored for later update of the GMMs.
        After calling this method for all paths in the training set,
        you need to call finishTrainIteration to do the update.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            path (BioKIT.Path):  matching path to the feature sequence

        """
        if len(fs) != len(path):
            raise ValueError("Path of length {} does not match feature sequence of length {}".format(len(path), len(fs)))

        if self.modelMapper == None:
            self.modelMapper = BioKIT.ModelMapper(self.topologyInfo,
                                                  self.mixtureTree,
                                                  self.atomMap)
        try:
            path = path.convertPath(self.atomMap, self.modelMapper)
        except:
            logger.log(BioKIT.LogSeverityLevel.Critical, "Error in path conversion")
            return

        self.traincount += 1
        if (self.trainer is None):
            if self.trainerType is TrainerType.MergeAndSplitTrainer:
                self.trainer = BioKIT.MergeAndSplitTrainer(self.gaussMixturesSet)
            else:
                self.trainer = BioKIT.GmmTrainer(self.gaussMixturesSet)

        self.trainer.accuPath(fs, path, 1.0)

    def finishTrainIteration(self):
        """
        Update the GMMs based on the accumulated data.

        The accumulated data are deleted afterwards. A new training
        iteration can be started by accumulating data after calling
        this function.

        The method also deletes all decoding results since it
        changes the models.
        """
        if (self.trainer is None):
            raise NoTrainerInitialized("Training was not initialized. No data stored for training.")
        self.clearDecodingList()

        # Is there data for every model?
        num_accus = self.trainer.getGaussMixtureAccuSet().getSize()
        num_gauss_mixtures = len(self.trainer.getGaussMixturesSet().getAvailableModelNames())
        if num_accus != num_gauss_mixtures:
            logger.warn("Only {} out of {} models have data to be trained on".format(num_accus, num_gauss_mixtures))

        # do training update
        self.trainer.doUpdate()

        if isinstance(self.trainer, BioKIT.MergeAndSplitTrainer):
            (splitCount, deleteCount) = self.trainer.splitGaussians()
            mergeCount = self.trainer.mergeGaussians()
            logger.info("Merge-And-Split Training: {} splits, {} deletions and {} merges".format(splitCount, deleteCount, mergeCount))

        self.trainer.clear()
        self.traincount = 0

    def initClustering(self, contextsize, minsamplecount, nrmaxleaves, nrofmixtures,
                       featuredimensionality, fillerAttribute="filler"):
        """
        Initialize the clustering to convert a context-independent model to a context-dependent model.

        Args:
            contextsize (int): maximum context to use in context-dependent
                models in number of atoms. Context is +/- contextsize, so if
                the desired context is an atom with its left and right
                neighbours the context size is 1.
            minsamplecount (int): minimum number of samples that have to be
                present in a context-dependent model after clustering to be
                considered valid
            nrmaxleaves (int): maximum number of context-dependent models
            nrofmixtures (int): the initial number of Gaussians per
                context-dependent model
            featuredimensionality (int): the number of dimensions of the
                context-dependent models
            fillerAttribute (str): the attribute in the dictionary that marks
                fillers
        """
        scorer = BioKIT.GmmFeatureVectorScorer(self.gaussMixturesSet)
        self.clusterer = BioKIT.ContextClusterer(scorer, self.modelMapper,
                                                 contextsize, self.dictionary,
                                                 fillerAttribute, minsamplecount,
                                                 nrmaxleaves, nrofmixtures,
                                                 featuredimensionality,
                                                 "DIAGONAL")

    def storeTokenSequenceForClustering(self, fs, listOfTokenNames,
                                   ignoreNoPathException=False,
                                   fillerToken = "filler",
                                   addFillerToBeginningAndEnd = False):
        """
        Add a sequence of tokens for clustering.

        This method must be called for every token sequence in the training data
        set. The method computes a Viterbi alignment of the given tokens
        with the feature sequence. The path is stored for later clustering of GMMs.
        After calling this method for all tokens sequences in the training set,
        you need to call cluster to do the update.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            listOfTokenNames (list of str): ordered list of token names, that
                are to be trained
            ignoreNoPathException (bool): if True, no exception is raised when no
                valid path could be found
            fillerToken (str): token to be used as filler
            addFillerToBeginningAndEnd (bool): if True, filler is added at the
                beginning and end of the token sequence

        Raises:
            NoViterbiPath: if no valid path could be found and
                ignoreNoPathException=False

        """
        if (self.clusterer is None):
            raise NoClustererInitialized('Cannot accumulate paths '
                                         'for clustering yet, have '
                                         'to call initClustering first!')

        try:
            path = self.forcedSequenceAlignment(fs, listOfTokenNames, fillerOrFillerTokenId=fillerToken, addFillerToBeginningAndEnd=addFillerToBeginningAndEnd)
            self.clusterer.accuPath(path, fs)
        except RuntimeError as e:
            if ignoreNoPathException:
                logger.log(BioKIT.LogSeverityLevel.Information, 'Ignoring error in forced alignment for %s,'
                                                                'error was: %s' % (listOfTokenNames, str(e)))
            else:
                logger.log(BioKIT.LogSeverityLevel.Information, "raise NoViterbiPath exception")
                raise NoViterbiPath(str(e))

    def storePathForClustering(self, fs, path):
        """
        Accumulate samples in given path for clustering process.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            path (BioKIT.Path): matching path to the feature sequence
        """
        if len(fs) != len(path):
            raise ValueError("Path of length {} does not match feature sequence of length {}".format(len(path), len(fs)))

        if (self.clusterer is None):
            raise NoClustererInitialized('Cannot accumulate paths '
                                         'for clustering yet, have '
                                         'to call initClustering first!')

        if self.modelMapper is None:
            self.modelMapper = BioKIT.ModelMapper(self.topologyInfo,
                                                  self.mixtureTree,
                                                  self.atomMap)
        try:
            path = path.convertPath(self.atomMap, self.modelMapper)
        except:
            logger.log(BioKIT.LogSeverityLevel.Critical, "Error in path conversion")
            return

        self.clusterer.accuPath(path, fs)

    def cluster(self):
        """
        Cluster atoms in their contexts to create a context-dependent model.

        Cluster atoms in their phonetic contexts as to create a context-
        dependent model. The context-dependent model is prepared, but needs to
        be initialized before it can be used (see initializeClusteredModels).
        The context of an atom is defined by the properties of its neighbouring
        atoms. Atom properties must exist in the atomMap to be considered.

        The resulting MixtureTree and ModelMapper are available as
        cd_mixtureTree and cd_modelMapper until the model is initialized.
        """
        if (self.clusterer is None):
            raise NoClustererInitialized('Cannot cluster yet have '
                                         'to call initClustering first!')
        self.cd_mixtureTree = self.clusterer.cluster()
        self.cd_contextSize = self.clusterer.getContextSize()
        self.cd_modelMapper = BioKIT.ModelMapper(self.topologyInfo,
                                                 self.cd_mixtureTree,
                                                 self.atomMap)
        self.clusterer = None
        self.samples = defaultdict(list)

    def storeTokenSequenceToInitClustered(self, fs, listOfTokenNames,
                                           ignoreNoPathException=False,
                                           fillerToken = "filler",
                                           addFillerToBeginningAndEnd = False):
        """
        Add a sequence of tokens to initialize a clustered model.

        This method must be called for every token sequence in the training data
        set. The method computes a Viterbi alignment of the given tokens
        with the feature sequence. The path is stored for later initialization of GMMs.
        After calling this method for all tokens sequences in the training set,
        you need to call initializeStoredModels to do the update.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            listOfTokenNames (list of str): ordered list of token names, that
                are to be trained
            ignoreNoPathException (bool): if True, no exception is raised when
                no valid path could be found
            fillerToken (str): token to be used as filler
            addFillerToBeginningAndEnd (bool): if True, filler is added at the
                beginning and end of the token sequence

        Raises:
            NoViterbiPath: if no valid path could be found and
                ignoreNoPathException=False

        """
        if not hasattr(self, 'cd_mixtureTree') or self.cd_mixtureTree is None:
            raise ValueError("No clustered mixture tree. Call cluster first.")

        try:
            path = self.forcedSequenceAlignment(fs, listOfTokenNames, fillerOrFillerTokenId=fillerToken, addFillerToBeginningAndEnd=addFillerToBeginningAndEnd)
            converted_path = path.convertPath(self.atomMap, self.cd_modelMapper)

            fsmatrix = fs.getMatrix()
            for i in range(0, converted_path.size()):
                modelName = self.cd_mixtureTree.getScorer().getModelName(converted_path[i].mModelId)
                self.storeSamplesForInit(modelName, fsmatrix, i, i + 1)
        except RuntimeError as e:
            if ignoreNoPathException:
                logger.log(BioKIT.LogSeverityLevel.Information, 'Ignoring error in forced alignment for %s,'
                                                                'error was: %s' % (listOfTokenNames, str(e)))
            else:
                logger.log(BioKIT.LogSeverityLevel.Information, "raise NoViterbiPath exception")
                raise NoViterbiPath(str(e))

    def storePathToInitClustered(self, fs, path):
        """
        Add a sequence of tokens to initialize a clustered model.

        This method must be called for every token sequence in the training data
        set. The method computes a Viterbi alignment of the given tokens
        with the feature sequence. The path is stored for later initialization of GMMs.
        After calling this method for all tokens sequences in the training set,
        you need to call initializeStoredModels to do the update.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            listOfTokenNames (list of str): ordered list of token names, that
                are to be trained
            ignoreNoPathException (bool): if True, no exception is raised when
                no valid path could be found
            fillerToken (str): token to be used as filler
            addFillerToBeginningAndEnd (bool): if True, filler is added at the
                beginning and end of the token sequence
        """
        if len(fs) != len(path):
            raise ValueError("Path of length {} does not match feature sequence of length {}".format(len(path), len(fs)))

        if not hasattr(self, 'cd_mixtureTree') or self.cd_mixtureTree is None:
            raise ValueError("No clustered mixture tree. Call cluster first.")

        try:
            converted_path = path.convertPath(self.atomMap, self.cd_modelMapper)

            fsmatrix = fs.getMatrix()
            for i in range(0, converted_path.size()):
                modelName = self.cd_mixtureTree.getScorer().getModelName(converted_path[i].mModelId)
                self.storeSamplesForInit(modelName, fsmatrix, i, i + 1)
        except:
            logger.log(BioKIT.LogSeverityLevel.Critical, "Error in path conversion")

    def initializeClusteredModels(self, clusteringAlgorithm="kmeans",
                                  useUniformCovariance = False,
                                  useUniformWeights = False):
        """
        Initialize the clustered models.

        Use the MixtureTree created in clustering to set up the model and
        run flatstart initialization based on the data accumulated by the method
        storeTokenSequenceToInitClustering.

        Args:
            clusteringAlgorithm (str): Algorithm used to cluster the data for
                the different components of a GMM.
                Options: kmeans and neuralGas. Default: kmeans
            useUniformCovariance (bool): initialize all variances uniformly to 1
                instead of using the variances of the k-means computed clusters.
                This used to be the standard behaviour and is here for legacy reasons.
            useUniformWeights (bool): initialize GMM with uniform weights for all Gaussians

        """
        # set the context dependend objects
        self.mixtureTree = self.cd_mixtureTree
        scorer = self.mixtureTree.getScorer()
        self.gaussMixturesSet = scorer.getGaussMixturesSet()
        self.gaussianContainerSet = self.gaussMixturesSet.getGaussianContainerSet()
        self.modelMapper  = self.cd_modelMapper
        #self.initSearchGraph()
        self.cd_mixtureTree = None
        self.cd_modelMapper = None
        self.trainer = None

        # initialize
        self.initializeStoredModels(clusteringAlgorithm, useUniformCovariance, useUniformWeights)

    def storeSamplesForInit(self, statename, matrix, start, end):
        """
        Store data for model initialization.

        Args:
            statename (str): name of the state to which the data belong
            matrix (numpy.array): data
            start (int): starting frame in the matrix to store
            end (int): final frame in the matrix to store (exclusive)

        """
        # because self.samples defaults to [] if key is not in dict, this works
        # ie, because self.samples = defaultdict(list) earlier
        self.samples[statename].append(matrix[start:end])

    def storeAtomForWKMInit(self, fs, atomname):
        """
        Store atom for later model initialization using WKM clustering.

        The mapping of states to feature vectors is done by applying
        warped k-means clustering for each of the given feature sequence.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            atomname (str): name of atom, which is to be initialized
        """
        numberOfStates = self.getNumberOfStates(atomname)

        statenames = ["%s-%s" % (atomname, state)
                      for state in range(numberOfStates)]

        data = fs.getMatrix().list()
        w = wkmb.WKM(data, len(statenames))
        w.cluster()
        #add end of feature sequence as last boundary
        boundaries = w.boundaries + [len(data) - 1]
        #state names is sorted from first to last state
        fsmatrix = fs.getMatrix()
        for i in range(len(statenames)):
            statename = statenames[i]
            self.storeSamplesForInit(statename, fsmatrix, boundaries[i], boundaries[i+1])

    def storeAtomForMultiWKMInit(self, fs, atomname):
        """
        Store atom for later multi-WKM clustering.

        The mapping of states to feature vectors is done by applying
        multi warped k-means clustering.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            atomname (str): name of atom, which is to be initialized
        """
        if not atomname in self.atomsamples:
            self.atomsamples[atomname] = []
        self.atomsamples[atomname].append(fs)

    def initializeAtomsMultiWKM(self):
        """Perform initialization with multi WKM."""
        for atomname, fslist in self.atomsamples.items():
            numberOfStates = self.getNumberOfStates(atomname)

            statenames = ["%s-%s" % (atomname, state)
                          for state in range(numberOfStates)]
            w = wkmb2.WKM([fs.getMatrix().list() for fs in fslist],
                          len(statenames), minsize=30)
            w.cluster_init()
            cont = True
            while cont:
                cont = w.cluster_iter()
            w.cluster_finalize()
            for idx, bound in enumerate(w.boundaries):
                data = w.samplelist[idx]
                boundaries = bound + [len(data) - 1]

                fsmatrix = fslist[idx].getMatrix()
                #state names is sorted from first to last state
                for i in range(len(statenames)):
                    statename = statenames[i]
                    self.storeSamplesForInit(statename, fsmatrix, boundaries[i], boundaries[i+1])

        self.initializeStoredModels()

    def initializeStoredModels(self, clusteringAlgorithm="kmeans",
                               useUniformCovariance = False,
                               useUniformWeights = False):
        """
        Initialize models using on the accumulated data.

        Args:
            clusteringAlgorithm (str): Algorithm used to cluster the data for
                the different components of a GMM.
                Options: kmeans and neuralGas. Default: kmeans
            useUniformCovariance (bool): initialize all variances uniformly to 1
                instead of using the variances of the k-means computed clusters.
                This used to be the standard behaviour and is here for legacy reasons.
            useUniformWeights (bool): initialize GMM with uniform weights for all Gaussians

        """
        if clusteringAlgorithm not in ["kmeans", "neuralGas"]:
            raise ValueError("Invalid clustering algorithm specified. Chose from 'kmeans' and 'neuralGas'")

        logger.log(BioKIT.LogSeverityLevel.Information, "Sample counts")
        num_samples = 0
        conc_samples = {}

        for key in sorted(self.samples):
            conc_samples[key] = np.copy(np.concatenate(self.samples[key], axis=0))
            logger.log(BioKIT.LogSeverityLevel.Information, '%30s: %5d x %5d' % (key, len(conc_samples[key]),
                                       len(conc_samples[key][0])))
            num_samples += len(conc_samples[key])

        logger.log(BioKIT.LogSeverityLevel.Information, "Total number of samples: {}".format(num_samples))
        logger.log(BioKIT.LogSeverityLevel.Information, "Total number of models:  {}".format(len(conc_samples)))

        # sanity check: need data for all models
        samples_names = set(conc_samples.keys())
        model_names = set(self.gaussianContainerSet.getGaussianContainerList())
        if samples_names != model_names:
            if len(samples_names-model_names) > 0:
                raise ValueError("For these names no models were defined: {}".format(samples_names - model_names))
            else:
                raise ValueError("There is no data for these models: {}\nModels cannot be initialized.".format(sorted(model_names - samples_names)))

        # shortcut
        gmmScorer = BioKIT.GmmFeatureVectorScorer(self.gaussMixturesSet)

        # cluster models
        for gcName in sorted(conc_samples):
            dim = self.gaussianContainerSet.getGaussianContainer(gcName).\
                getDimensionality()
            logger.log(BioKIT.LogSeverityLevel.Information, 'Clustering (' + clusteringAlgorithm + ') for ' + gcName)
            gc = self.gaussianContainerSet.getGaussianContainer(gcName)
            assert dim == gc.getDimensionality()

            mx = self.gaussMixturesSet.getGaussMixture(
                gmmScorer.getModelIdFromString(gcName))
            numberOfGaussians = gc.getGaussiansCount()

            data = np.array(conc_samples[gcName])
            if clusteringAlgorithm == "kmeans":
                maxIter = 10
                (means, variances, assigns) = BioKIT.Algorithms.kMeans(
                    data, numberOfGaussians, maxIter, True)
            elif clusteringAlgorithm == "neuralGas":
                maxIter = 1000
                (means, variances, assigns) = \
                    BioKIT.Algorithms.neuralGasClustering(
                        data, numberOfGaussians, maxIter, True)

            for gaussian in range(0, numberOfGaussians):
                gc.setMeanVector(gaussian, means[gaussian])
                if useUniformCovariance:
                    covMatrix = BioKIT.DiagonalCovMatrix(np.ones(dim))
                else:
                    covMatrix = BioKIT.DiagonalCovMatrix(variances[gaussian])
                gc.setCovarianceMatrix(gaussian, covMatrix)
                gCount = gc.getGaussiansCount()
            if useUniformWeights:
                mixWeights = np.ones(gCount) / (1.0 * gCount)
            else:
                mixWeights = list(range(gCount))
                mixWeights = [(assigns.count(x) * 1.0) / len(assigns) for x in mixWeights]
            mx.setMixtureWeights(mixWeights)

            #logger.log(BioKIT.LogSeverityLevel.Information, "Gaussian number " + str(gaussian) + ":")
            #logger.log(BioKIT.LogSeverityLevel.Information, "Mean: " + str(thisMean))
            #logger.log(BioKIT.LogSeverityLevel.Information, "Covariance matrix: " + str(covMatrix.getData()))
            #logger.log(BioKIT.LogSeverityLevel.Information, "Mixture Weights: " + str(mixWeights))
            #logger.log(BioKIT.LogSeverityLevel.Information, "\n")

    def getNumberOfStates(self, atomname):
        """
        Get the number of states for an atom.

        Args:
            atomname (str): Atom
        """
        atom = self.atomMap.getAtom(atomname)
        ac = BioKIT.AtomContext([atom], 0, self.atomMap)
        topologies = self.topologyInfo.findTopologies(ac)
        assert len(topologies) == 1
        topology = topologies[0][1]
        rootNodes = topology.getRootNodes()
        return(len(rootNodes))

    def storeAtomForInit(self, fs, atomname):
        """
        Store a feature sequence and corresponding atom for initialization.

        Data is stored for flatstart initialization. The feature sequence is
        sliced into parts of equal length, corresponding to the number
        of HMM states.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            atomname (str): name of atom, which is to be initialized
        """
        numberOfStates = self.getNumberOfStates(atomname)
        statenames = ["%s-%s" % (atomname, state)
                      for state in range(numberOfStates)]

        framesperstate = int(fs.getLength() / numberOfStates)
        additionalframes = fs.getLength() % numberOfStates

        fsmatrix = fs.getMatrix()
        currentsample = 0
        for statename in statenames:
            if additionalframes > 0:
                nrFrames = framesperstate + 1
                additionalframes -= 1
            else:
                nrFrames = framesperstate
            self.storeSamplesForInit(statename, fsmatrix, currentsample,
                                     currentsample + nrFrames)
            currentsample += nrFrames

    def storeTokenForInit(self, fs, tokenname):
        """
        Store a feature sequence and corresponding token for initialization.

        Data is stored for flatstart initialization. The feature sequence is
        sliced into parts of equal length, corresponding to the number
        of atoms the token consists of.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            tokenname (str): name of token, which is to be initialized
        """
        #TODO: AUSSPRACHEVARIANTEN !

        for i in self.dictionary.getTokenIds(tokenname):
            entry = self.dictionary.getDictionaryEntry(i)
            featureDim = fs.getDimensionality()
            atomIds = entry.getAtomIdList()

            framelen = int(fs.getLength() / len(atomIds))
            start = 0
            end = start + framelen
            for atomId in atomIds:
                subFs = BioKIT.FeatureSequence()
                subFs.setMatrix(fs.getMatrix()[start:end, :])
                self.storeAtomForInit(subFs,
                                      self.atomMap.findAtomName(atomId))
                start = start + framelen
                end = min(end + framelen, len(fs.getMatrix()))

    def storeTokenSequenceForInit(self, fs, listOfTokenNames,
                                  fillerToken = "filler",
                                  addFillerToBeginningAndEnd = False):
        """
        Store a feature sequence and corresponding token sequence for initialization.

        Data is stored for flatstart initialization. The feature sequence is
        sliced into parts of equal length, corresponding to the number
        of atoms the token sequence consists of.

        Args:
            fs (BioKIT.FeatureSequence): a sample Feature Sequence
            listOfTokenNames (list of str): ordered list of token names, that
                are to be trained
            fillerToken (str): token to be used as filler
            addFillerToBeginningAndEnd (bool): if True, filler is added at the
                beginning and end of the token sequence
        """
        #TODO: AUSSPRACHEVARIANTEN !

        if addFillerToBeginningAndEnd:
            listOfTokenNames[:0] = fillerToken
            listOfTokenNames.append(fillerToken)

        atomIds = []
        for tokenname in listOfTokenNames:
            tokenIds = self.dictionary.getTokenIds(tokenname)

            entry = self.dictionary.getDictionaryEntry(tokenIds[0])
            tokenatomIds = entry.getAtomIdList()
            atomIds.extend(tokenatomIds)

        framelen = len(fs) / len(atomIds)
        start_idx = 0
        end = start_idx + framelen
        end_idx = int(end)
        for atomId in atomIds:
            subFs = fs[start_idx:end_idx]
            self.storeAtomForInit(subFs,
                                  self.atomMap.findAtomName(atomId))
            start_idx = end_idx
            end = min(end + framelen, len(fs))
            end_idx = int(end)

        # make sure we don't lose the end
        if start_idx < len(fs):
            end_idx = len(fs)
            subFs = fs[start_idx:end_idx]
            self.storeAtomForInit(subFs,
                                  self.atomMap.findAtomName(atomId))


    def storePathForInit(self, fs, path):
        """
        Store a feature sequence and corresponding search path for initialization.

        The information which parts of the feature sequence correspond to
        which model are taken from the path.

        Args:
            fs (BioKIT.FeatureSequence): a feature sequence
            path (BioKIT.Path): matching path to the feature sequence

        """
        if len(fs) != len(path):
            raise ValueError("Path of length {} does not match feature sequence of length {}".format(len(path), len(fs)))

        if self.modelMapper == None:
            self.modelMapper = BioKIT.ModelMapper(self.topologyInfo,
                                                  self.mixtureTree,
                                                  self.atomMap)
        try:
            path = path.convertPath(self.atomMap, self.modelMapper)
        except:
            logger.log(BioKIT.LogSeverityLevel.Critical, "Error in path conversion")
            return

        fsmatrix = fs.getMatrix()
        for i in range(0, path.size()):
            modelName = self.gaussMixturesSet.getModelName(path[i].mModelId)
            self.storeSamplesForInit(modelName, fsmatrix, i, i+1)

    def saveToFiles(self, path):
        """
        Save the Recognizer on disk.

        Includes the definitions and trained models, so that
        the Recognizer can be re-loaded.

        Args:
            path (str): path of directory, where the files should be stored

        """
        if not os.path.exists(path):
            os.makedirs(path)

        self.gaussianContainerSet.writeDescFile(os.sep.join([path,
                                                             "gaussianDesc"]))
        self.gaussianContainerSet.saveDataFile(os.sep.join([path,
                                                            'gaussianData']))
        self.gaussMixturesSet.writeDescFile(os.sep.join([path, 'mixtureDesc']))
        self.gaussMixturesSet.saveDataFile(os.sep.join([path, 'mixtureData']))
        self.mixtureTree.writeTree(os.sep.join([path, 'mixtureTree']))
        self.topologyInfo.writeTopologyTree(os.sep.join([path,
                                                         'topologyTree']))
        self.topologyInfo.writeTopologies(os.sep.join([path, 'topologies']))
        self.atomMap.writeAtomManager(os.sep.join([path, "atomMap"]))

        #dictionary has no write method
        #TODO: Currently ignores fillers, do we need it anyway?
        with open(os.sep.join([path, "dictionary"]), "w") as f:
            tokens = sorted(self.dictionary.getTokenList())
            for token in tokens:
                ids = self.dictionary.getTokenIds(token)
                for id in ids:
                    entry = self.dictionary.getDictionaryEntry(id)
                    atomlist = entry.getAtomIdList()
                    atomlist = [self.atomMap.getAtom(x).getName() for x in atomlist]
                    attributelist = entry.getAttributeList()
                    attributelist = ["[{} {}]".format(attribute, attributelist[attribute]) for attribute in attributelist]
                    f.write("%s {%s} %s\n" % (token, " ".join(atomlist), " ".join(attributelist)))

    def clearDecodingList(self):
        """Erase every previous decoding result."""
        self.decodingResultList = []
        self.decodecount = 0
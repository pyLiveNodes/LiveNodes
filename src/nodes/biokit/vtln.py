# python-lib
import logger

import BioKIT


class VtlnWrapper:

  def __init__(self, dictionary, modelMapper, scorer, hypoBeam, hypoTopN, finalHypoBeam, finalHypoTopN, latticeBeam, tokenSequenceModelWeight, tokenInsertionPenalty, preprocessingChain):
    self.__modelMapper = modelMapper
    self.__dictionary = dictionary
    self.__scorer = scorer
    self.__hypoBeam = hypoBeam
    self.__hypoTopN = hypoTopN
    self.___finalHypoBeam = finalHypoBeam
    self.__finalHypoTopN = finalHypoTopN
    self.__latticeBeam = latticeBeam
    self.__tokenSequenceModelWeight = tokenSequenceModelWeight
    self.__tokenInsertionPenalty = tokenInsertionPenalty
    self.__preprocessingChain = preprocessingChain
    self.__parameter_range = [0.8 + 0.02 * x for x in range(0, 21)]

  # reference must contain pronounciation variants
  # mcfs represents features from the PP step just before applying mel filterbank
  # TODO: currently only supports single feature sequence
  def estimateParameter(self, references, mcfss):

    scoresByParam = {}
    for param in self.__parameter_range:
      scoresByParam[param] = 0.0

    #try different factors for beams if a path cannot be traced
    beamFactor = 1

    #number the current beam factor is multiplied with to get the next beam factor
    beamStep = 2

    #maximum beam factor allowed before skipping the utterance completely
    beamMax = 8

    i = 0
    while (i < len(references)):
      skipUtterance = False
      logger.log(BioKIT.LogSeverityLevel.Information, "utterance " + str(i) + " with beam factor " + str(beamFactor))

      #print "evaluate reference " + str(i)
      # extract current reference and feature sequence
      reference = references[i]
      print("evaluate reference " + str(reference))
      mcfs = mcfss[i]

      # generate list of token ids

      tokens = reference
      tokenIds = []
      for token in tokens.split():
        tokenId = self.__dictionary.getBaseFormId(token)
        tokenIds.append(tokenId)

      # instantiate search graph handler and decoder

      fillWordId = self.__dictionary.getBaseFormId("$")

      #set pruning parameters
      hypoBeam = beamFactor * self.__hypoBeam
      hypoTopN = beamFactor * self.__hypoTopN
      finalHypoBeam = beamFactor * self.___finalHypoBeam
      finalHypoTopN = beamFactor * self.__finalHypoTopN
      latticeBeam = beamFactor * self.__latticeBeam

      beams = BioKIT.Beams(hypoBeam, hypoTopN, finalHypoBeam, finalHypoTopN, latticeBeam)

      sgh = BioKIT.SearchGraphHandler(self.__dictionary, tokenIds, fillWordId, self.__modelMapper, self.__scorer, beams, self.__tokenSequenceModelWeight, self.__tokenInsertionPenalty)
      __vtln_decoder = BioKIT.Decoder(sgh)

      #search parameter space
      currentScoresByParam = {}
      for param in self.__parameter_range:
          currentScoresByParam[param] = 0.0

      repeatUtterance = False
      for param in self.__parameter_range:
        #print "evaluate parameter " + str(param)
        warpedFeatureSequence = self.__preprocessingChain.execute(mcfs, vtlnWarpingFactor= param)
        __vtln_decoder.search(warpedFeatureSequence, True)
        result = __vtln_decoder.extractSearchResult()

        #test if we have a result
        if(len(result) > 0):
            currentScoresByParam[param] = result[0].score
        else:
            #increase beam size and redo utterance
            beamFactor = beamStep * beamFactor
            if(beamFactor <= beamMax):
                repeatUtterance = True
            else:
                beamFactor = 1
                skipUtterance = True
                logger.log(BioKIT.LogSeverityLevel.Information, "Skipping utterance")
            break

      if not repeatUtterance:
        i = i + 1; #increment i for next utterance
        if not skipUtterance:
          #reset beam factor
          beamFactor = 1

          #accumulate scores if current utterance was not skipped
          for param in self.__parameter_range:
             scoresByParam[param] = scoresByParam[param] + currentScoresByParam[param]

    # average scores over all utterances in tuning set for ML selection of parameter
    bestScore = float("inf")
    for param in self.__parameter_range:
      score = scoresByParam[param]
      if score < bestScore:
        bestScore = score
        bestParam = param
        #print "param: " + str(param) + ", score: " + str(score)
    return bestParam

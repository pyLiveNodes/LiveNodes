import BioKIT
import numpy
import adc

class PrePro:
    """This class implements the standard Airwriting preprocessing method"""
    
    inputDataFileReader = BioKIT.InputDataFileReader()
    windowFramer = BioKIT.WindowFramer()
    averageCalculator = BioKIT.AverageExtractor()
    meanSubtraction = BioKIT.ZNormalization()
    channelRecombination = BioKIT.ChannelRecombination()
    
    def __init__(self):
        self.duration = None
    
    def process(self, adcPath):
        """
        Process one given adc file and return a MultiChannelFeatureSequence
        """
        samplingRate = 819.2
        adcOffset = 0
        numChannels = 7
        frameLength = int(samplingRate * 0.01)
        frameShift = 0
        #log("Info", "Preprocessing " + adcPath)
        data = self.inputDataFileReader.readFile(str(adcPath),
             BioKIT.SF_FORMAT.RAW | BioKIT.SF_FORMAT.PCM_16, int(samplingRate),
             numChannels, 0, 0, adcOffset)
        self.duration = data[0].getLength()/float(samplingRate)
        #delete first channel which contains the counter
        del data[0]
        data = self.windowFramer.applyWindow(data, frameLength, frameShift,
                                             BioKIT.WindowType.rectangular)
        data = self.averageCalculator.calculateFrameBasedAverage(data)
        self.meanSubtraction.resetMeans()
        self.meanSubtraction.updateMeans(data, 1.0, True)
        data = self.meanSubtraction.subtractMeans(data, 1.0)
        data = self.channelRecombination.performFeatureFusion(data)
        return data
    
    def getFeatureDim(self):
        """Return the dimensionality of the feature space"""
        return 6
   
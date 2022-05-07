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
    
    def process(self, adcPath, **kwargs):
        """
        Process one given adc file and return a MultiChannelFeatureSequence
        """
        samplingRate = 102 
        adcOffset = 0
        numChannels = 6
        #log("Info", "Preprocessing " + adcPath)
        data = self.inputDataFileReader.readFile(str(adcPath),
             BioKIT.SF_FORMAT.RAW | BioKIT.SF_FORMAT.PCM_16, samplingRate,
             numChannels, 0, 0, adcOffset)
        data = self.channelRecombination.performFeatureFusion(data)
        return data
    
   

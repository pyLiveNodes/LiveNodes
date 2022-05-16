#
# This class contains general filter design routines.
#
# Currently available:
#   * SimpleHighPassImpulseResponse - a steep highpass filter

from . import BioKIT
import math


## TODO get similiar methods for lowPass, band pass and notch filters
#
def simpleHighPassImpulseResponse(length, cutoff):
    """
    Returns the impulse response of a simple highPass filter.
    The resulting filter has a fairly steep slope,
    but introduces some phase distortion. 
    Please use more sophisticated methods if you need phase minimal filtering.
     
    parameters: length - the order of the filter
                cutoff - between 0 and 1, the cutoff relative to nyquist frequency
    """
    mWindowLength = int(length + 1)
    impulseResponse = BioKIT.NumericVector()

    # clip cutoff between 0 and 1:
    cutoff = max(min(cutoff, 1.0), 0.0)

    impulseResponse.resize(mWindowLength)

    # init filter with hamming window...
    temp = 2.0 * math.pi / (1.0 * (length))
    for k in range(mWindowLength):
        impulseResponse.set(k, 0.54 - 0.46 * math.cos(temp * k))

    #calculate High Pass Filter
    value = 0.0
    half = length / 2.0
    for k in range(mWindowLength):
        a = math.pi * (k - half)
        if (a == 0.0):
            value = cutoff
        else:
            value = math.sin(math.pi * cutoff * (k - half)) / a
        impulseResponse.set(k, -1.0 * impulseResponse.get(k) * value)

    impulseResponse.set(mWindowLength / 2,
                        impulseResponse.get(mWindowLength / 2) + 1)
    return impulseResponse

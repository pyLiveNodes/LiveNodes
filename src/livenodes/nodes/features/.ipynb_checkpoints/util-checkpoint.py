import numpy as np
import scipy.stats
from functools import partial

def matchLastDimByRepeat(values, wts):
    return np.repeat(np.expand_dims(values, axis=-1), np.ma.size(wts, axis=-1), axis=-1)


def lastDimToMatchShape(arr, targetArr):
    return np.tile(arr, np.shape(targetArr)[:-1] + (1,))


def compute_time(signal, fs):
    """Creates the signal correspondent time array.

    Parameters
    ----------
    signal: nd-array
        Input from which the time is computed.
    fs: int
        Sampling Frequency

    Returns
    -------
    time : float list
        Signal time

    From: https://tsfel.readthedocs.io/en/latest/_modules/tsfel/feature_extraction/features_utils.html#kde


    """

    return lastDimToMatchShape(np.arange(0, np.ma.size(signal, axis=-1) / fs, 1./fs), signal)


def divideWithZero(a, b, out=np.zeros_like):
    return np.divide(a, b, out=out(b), where=b != 0)

def calc_fft(signal, sf):
    """ This functions computes the fft of a signal.

    Assumption
    ----------
    This is a well behaved ndarray in which each dimension has the same length.
    willma.ill fail / the wrong dimension is used, as numpy will (likely) flatten all mismatching dimensions below

    Parameters
    ----------
    signal : nd-array
        The input signal from which fft is computed
    sf : int
        Sampling frequency

    Returns
    -------
    f: nd-array
        Frequency values (xx axis)
    fmag: nd-array
        Amplitude of the frequency values (yy axis)

    From: https://tsfel.readthedocs.io/en/latest/_modules/tsfel/feature_extraction/features_utils.html#kde

    """

    fmag = np.abs(np.fft.rfft(signal, axis=-1))
    signalLength = np.ma.size(signal, axis=-1) // 2
    f = np.linspace(0, sf // 2, signalLength)

    # as we already assumed they all have the same length and the same sf, we can just bring f to the same shape as the fmag return value

    fmag_ret = fmag[..., :signalLength]
    f_ret = lastDimToMatchShape(f, fmag_ret)

    return f_ret, fmag_ret


# TODO: evaluate and switch sometime
def calc_fft_new(signal, sf):
    """ 
    FFT with frrtfreq as done in np documentation
    see: https://numpy.org/doc/stable/reference/routines.fft.html#module-numpy.fft
    
    Note: the fft includes the zero-frequency component by default
    
    IMPORTANT: this is not equivalent to legacy, which is based on tsfel.
    The two are compatabile if:
    sf := sampling frequence
    a = np.linspace(0, sf // 2, signal.shape[-1] // 2 + 1) # note the + 1 in linspace
    b = np.fft.rfftfreq(signal.shape[-1], d=1/sf)

    """

    fmag = np.abs(np.fft.rfft(signal, axis=-1))
    f = np.fft.rfftfreq(signal.shape[-1], d=1/sf)
    # as we already assumed they all have the same length and the same sf, we can just bring f to the same shape as the fmag return value
    f_ret = lastDimToMatchShape(f, fmag)
    return f_ret, fmag


def calc_ecdf(wts):
    return np.sort(wts, axis=-1), np.arange(1, np.ma.size(wts, axis=-1)+1) / np.ma.size(wts, axis=-1)


def vectorized(fn, X, **fnArgs):
    res = np.array([fn(ts, **fnArgs) for ts in X.reshape(-1, X.shape[-1])])
    return res.reshape(X.shape[:-1]) if res.size == np.prod(X.shape[:-1]) else res.reshape((*X.shape[:-1], -1))


def create_xx(features):
    """Computes the range of features amplitude for the probability density function calculus.
    Parameters
    ----------
    features : nd-array
        Input features
    Returns
    -------
    nd-array
        range of features amplitude
    """

    min_f = np.min(features, axis=-1)
    max_f = np.abs(np.max(features, axis=-1))
    max_f = np.where(min_f != max_f, max_f, max_f + 10)
    
    return np.linspace(min_f, max_f, np.ma.size(features, axis=-1)) \
            .transpose(np.append(np.arange(1, features.ndim), 0))

def kde(features):
    pass
    """Computes the probability density function of the input signal using a Gaussian KDE (Kernel Density Estimate)
    Parameters
    ----------
    features : nd-array
        Input from which probability density function is computed
    Returns
    -------
    nd-array
        probability density values
    """
    features_ = np.copy(features)
    xx = create_xx(features)
    
    min_f = np.expand_dims(np.min(features, axis=-1), axis=-1)
    # TODO: the original implementation did not use the abs here like it did in the create_xx, should be further investigated, might be an error
    max_f = np.expand_dims(np.max(features, axis=-1), axis=-1)
    noise = np.random.standard_normal(features.shape) * 0.0001
    features_ = np.where(min_f != max_f, features, features + noise)

    # essentially: 
    # 1. flatten the whole thing
    # 2. then run the original part on each flat instance
    # 3. reshape to original shape
    
    # usually i wouldn't bother, but this part is needed for the otherwise more efficient gaussian param estimation
    
    flat = features_.reshape(-1, features_.shape[-1])
    flat_xx = xx.reshape(-1, xx.shape[-1])
    res = np.array([scipy.stats.gaussian_kde(z[0], bw_method='silverman')(z[1]) for z in zip(flat, flat_xx)])
    
    kernel = res.reshape(features_.shape[:-1]) if res.size == np.prod(features_.shape[:-1]) else res.reshape((*features_.shape[:-1], -1))

    return np.array(kernel / np.expand_dims(np.sum(kernel, axis=-1), axis=-1))

def gaussian(features):
    """Computes the probability density function of the input signal using a Gaussian function
    Parameters
    ----------
    features : nd-array
        Input from which probability density function is computed
    Returns
    -------
    nd-array
        probability density values
    """

    xx = create_xx(features)
    std_value = np.expand_dims(np.std(features, axis=-1), axis=-1)
    mean_value = np.expand_dims(np.mean(features, axis=-1), axis=-1)
    
    pdf_gauss = scipy.stats.norm.pdf(xx, mean_value, std_value)
    
    return np.where(std_value == 0, 0.0, \
                   np.array(pdf_gauss / np.expand_dims(np.sum(pdf_gauss, axis=-1), axis=-1)))

import numpy as np
import scipy.stats

from .util import matchLastDimByRepeat, lastDimToMatchShape, compute_time, divideWithZero, kde, gaussian, vectorized, calc_ecdf

# === Single out ====================================================================================================


def raw(x):
    return x


def __autocorr(x):
    return np.correlate(x, x)


# NOTE: This does not seem to be easily doable without for loops, as neither numpy nor scipy offer a multi version
# TODO: I cannot imagine the math not to be done already, so check if this can be implemented easily directly.
def autocorr(wts):
    # essentially: flatten to 2dim if necessary, so that list of windows
    # then calc autocorr and reshape to original shape without last dimension, as correlate returns a single float
    # Note: this is not more efficient than before, it just allows for multichannel input
    return vectorized(__autocorr, wts)


def calc_centroid(wts, samplingfrequency):
    time = compute_time(wts, samplingfrequency)

    energy = wts**2

    t_energy = np.sum(time * energy, axis=-1)
    energy_sum = np.sum(energy, axis=-1)
    return divideWithZero(t_energy, energy_sum)


def minpeaks(wts):
    return np.sum(np.diff(np.sign(np.diff(wts))) == 2, axis=-1)


def maxpeaks(wts):
    return np.sum(np.diff(np.sign(np.diff(wts))) == -2, axis=-1)


def mean_abs_diff(wts):
    return np.mean(np.abs(np.diff(wts)), axis=-1)


def mean_diff(wts):
    return np.mean(np.diff(wts), axis=-1)


def median_abs_diff(wts):
    return np.median(np.abs(np.diff(wts)), axis=-1)


def median_diff(wts):
    return np.median(np.diff(wts), axis=-1)


def distance(wts):
    return np.sum(np.sqrt(np.diff(wts)**2 + 1), axis=-1)


def sum_abs_diff(wts):
    return np.sum(np.abs(np.diff(wts)), axis=-1)


def zero_cross(wts):
    return np.sum(np.abs(np.diff(np.sign(wts))) == 2, axis=-1)


def total_energy(wts, samplingfrequency):
    t = compute_time(wts, samplingfrequency)
    return np.sum(
        wts**2, axis=-1) / (np.ma.size(wts, axis=-1) / 1. / samplingfrequency -
                            1. / samplingfrequency)


def auc(wts, samplingfrequency):
    t = compute_time(wts, samplingfrequency)
    return np.sum(0.5 * np.diff(t, axis=-1) *
                  np.abs(wts[..., :-1] + wts[..., 1:]),
                  axis=-1)


def abs_energy(wts):
    return np.sum(wts**2, axis=-1)


def pk_pk_distance(wts):
    return np.abs(np.max(wts, axis=-1) - np.min(wts, axis=-1))


def interq_range(wts):
    return np.percentile(wts, 75, axis=-1) - np.percentile(wts, 25, axis=-1)


def kurtosis(wts):
    return scipy.stats.kurtosis(wts, axis=-1)


def skewness(wts):
    return scipy.stats.skew(wts, axis=-1)


def slope(wts):
    # polyfit supports up to two dimensions, since the slope should be independent (because it is calculated on the last dimension, which is not implicated by reshaping the first dimensions, which is what we are doing): reshape into two dim, calc and then reshape back into orig shape
    shape = wts.shape
    tmp = wts.reshape((-1, shape[-1])).T
    t = np.linspace(0, tmp.shape[0] - 1, tmp.shape[0])
    return np.polyfit(t, tmp, 1)[0].T.reshape(shape[:-1])


def calc_max(wts):
    return np.max(wts, axis=-1)


def calc_min(wts):
    return np.min(wts, axis=-1)


def calc_mean(wts):
    return np.mean(wts, axis=-1)


def calc_median(wts):
    return np.median(wts, axis=-1)


def mean_abs_deviation(wts):
    return np.mean(np.abs(wts -
                          matchLastDimByRepeat(np.mean(wts, axis=-1), wts)),
                   axis=-1)


def median_abs_deviation(wts):
    return scipy.stats.median_absolute_deviation(wts, scale=1, axis=-1)


def rms(wts):
    return np.sqrt(np.mean(np.square(wts), axis=-1))


def calc_std(wts):
    return np.std(wts, axis=-1)


def calc_var(wts):
    return np.var(wts, axis=-1)


def calc_cumsum_max(wts):
    return np.max(np.cumsum(wts, axis=-1), axis=-1)


def calc_sum(wts):
    return np.sum(wts, axis=-1)


def __entropy(p):
    normTerm = np.log2(np.count_nonzero(p, axis=-1))
    p_without_null = np.ma.masked_equal(p, 0)

    entr = -np.sum(p_without_null * np.log2(p_without_null),
                   axis=-1) / normTerm

    return np.where(np.sum(p, axis=-1) == 0, 0, entr)


# @profile
# TODO: why don't we just use the standard implementation again?
# https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.entropy.html
def entropy(wts, prob='kde'):
    if prob == 'gauss':
        p = gaussian(wts)
    elif prob == 'kde':
        p = kde(wts)
    else:
        raise Exception("Unknown prob estimator")

    return __entropy(p)


def ecdf(wts, d=10):
    _, y = calc_ecdf(wts)
    return lastDimToMatchShape(y[:d], wts)


def ecdf_slope(wts, p_init=0.5, p_end=0.75):
    isConstant = np.sum(np.diff(wts, axis=-1), axis=-1) == 0
    percentiles = ecdf_percentile(wts, [p_init, p_end])
    vals = (p_end - p_init) / (percentiles[..., 1] - percentiles[..., 0])
    return np.where(isConstant, np.inf, vals)


def ecdf_percentile(wts, percentile=[0.2, 0.8]):
    x, y = calc_ecdf(wts)

    isConstant = np.repeat(np.expand_dims(np.sum(np.diff(wts, axis=-1),
                                                 axis=-1),
                                          axis=-1) == 0,
                           len(percentile),
                           axis=-1)

    maxs = np.stack([np.max(x[..., y <= p], axis=-1) for p in percentile],
                    axis=-1).reshape(isConstant.shape)
    res = np.where(isConstant, wts[..., :len(percentile)], maxs)

    # this is the original tsfel behaviour, but shouln't we still return an array here?
    if len(percentile) == 1:
        return res[0]
    else:
        return res


def ecdf_percentile_count(wts, percentile=[0.2, 0.8]):
    x, y = calc_ecdf(wts)

    isConstant = np.repeat(np.expand_dims(np.sum(np.diff(wts, axis=-1),
                                                 axis=-1),
                                          axis=-1) == 0,
                           len(percentile),
                           axis=-1)

    counts = np.stack(
        [np.count_nonzero(x[..., y <= p], axis=-1) for p in percentile],
        axis=-1).reshape(isConstant.shape)
    res = np.where(isConstant, wts[..., :len(percentile)], counts)

    # this is the original tsfel behaviour, but shouln't we still return an array here?
    if len(percentile) == 1:
        return res[0]
    else:
        return res


# === Multiple out ====================================================================================================

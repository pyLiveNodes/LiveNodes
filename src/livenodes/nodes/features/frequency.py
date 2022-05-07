import numpy as np
import scipy.signal

from .util import matchLastDimByRepeat, divideWithZero, calc_fft
from .statistical import maxpeaks, __entropy

# === Single out ====================================================================================================


def spectral_distance(wts, samplingfrequency):
    _, fmag = calc_fft(wts, samplingfrequency)

    cum_fmag = np.cumsum(fmag, axis=-1)

    # Compute the linear regression
    # TODO: there must be a nicer version than this transpose...
    points_y = np.linspace(0, cum_fmag[..., -1], np.ma.size(cum_fmag, axis=-1))
    points_y = points_y.transpose(np.append(np.arange(1, wts.ndim), 0))

    return np.sum(points_y - cum_fmag, axis=-1)


def max_power_spectrum(wts, samplingfrequency):
    wts = np.copy(wts)
    norm = matchLastDimByRepeat(np.std(wts, axis=-1), wts)
    wts = np.divide(wts, norm, out=wts, where=norm != 0)

    return np.max(scipy.signal.welch(wts,
                                     int(samplingfrequency),
                                     nperseg=wts.shape[-1],
                                     axis=-1)[1],
                  axis=-1)


def max_frequency(wts, samplingfrequency):
    f, fmag = calc_fft(wts, samplingfrequency)

    cum_fmag = np.cumsum(fmag, axis=-1)
    expanded = matchLastDimByRepeat(np.take(cum_fmag, -1, axis=-1), cum_fmag)

    try:
        ind_mag = np.argmax(np.array(np.asarray(cum_fmag > expanded * 0.95)),
                            axis=-1)
    except IndexError:
        ind_mag = np.argmax(cum_fmag, axis=-1)

    ind_mag = np.expand_dims(ind_mag, axis=-1)
    return np.squeeze(np.take(f, ind_mag), axis=-1)


def median_frequency(wts, samplingfrequency):
    f, fmag = calc_fft(wts, samplingfrequency)

    cum_fmag = np.cumsum(fmag, axis=-1)
    expanded = matchLastDimByRepeat(np.take(cum_fmag, -1, axis=-1), cum_fmag)

    try:
        ind_mag = np.argmax(np.array(np.asarray(cum_fmag > expanded * 0.5)),
                            axis=-1)
    except IndexError:
        ind_mag = np.argmax(cum_fmag, axis=-1)

    ind_mag = np.expand_dims(ind_mag, axis=-1)
    return np.squeeze(np.take(f, ind_mag), axis=-1)


def spectral_centroid(wts, samplingfrequency):
    f, fmag = calc_fft(wts, samplingfrequency)
    summedFmag = matchLastDimByRepeat(np.sum(fmag, axis=-1), fmag)
    return np.sum(f * divideWithZero(fmag, summedFmag), axis=-1)


def spectral_decrease(wts, samplingfrequency):
    f, fmag = calc_fft(wts, samplingfrequency)

    fmag_band = fmag[..., 1:]
    len_fmag_band = np.arange(1, np.ma.size(fmag, axis=-1))

    # Sum of numerator
    soma_num = np.sum(
        (fmag_band - matchLastDimByRepeat(fmag[..., 0], fmag_band)) /
        len_fmag_band,
        axis=-1)

    return divideWithZero(1, np.sum(fmag_band, axis=-1)) * soma_num


def spectral_kurtosis(wts, samplingfrequency):
    f, fmag = calc_fft(wts, samplingfrequency)
    spect_centr = spectral_centroid(wts, samplingfrequency)
    spread = spectral_spread(wts, samplingfrequency)
    summedFmag = matchLastDimByRepeat(np.sum(fmag, axis=-1), fmag)

    spect_kurt = (
        (f - matchLastDimByRepeat(spect_centr, f))**4) * (fmag / summedFmag)
    return divideWithZero(np.sum(spect_kurt, axis=-1), spread**4)


def spectral_skewness(wts, samplingfrequency):
    f, fmag = calc_fft(wts, samplingfrequency)
    spect_centr = spectral_centroid(wts, samplingfrequency)
    summedFmag = matchLastDimByRepeat(np.sum(fmag, axis=-1), fmag)

    skew = (
        (f - matchLastDimByRepeat(spect_centr, f))**3) * (fmag / summedFmag)
    return divideWithZero(np.sum(skew, axis=-1),
                          spectral_spread(wts, samplingfrequency)**3)


def spectral_spread(wts, samplingfrequency):
    f, fmag = calc_fft(wts, samplingfrequency)
    spect_centroid = spectral_centroid(wts, samplingfrequency)
    helper = (f - matchLastDimByRepeat(spect_centroid, f))**2
    summedFmag = matchLastDimByRepeat(np.sum(fmag, axis=-1), fmag)
    return np.sum(helper * divideWithZero(fmag, summedFmag), axis=-1)**0.5


def spectral_slope(wts, samplingfrequency):
    f, fmag = calc_fft(wts, samplingfrequency)
    num_ = divideWithZero(1, np.sum(
        fmag, axis=-1)) * (np.ma.size(f, axis=-1) * np.sum(f * fmag, axis=-1) -
                           np.sum(f, axis=-1) * np.sum(fmag, axis=-1))
    denom_ = np.ma.size(f, axis=-1) * np.sum(f * f, axis=-1) - np.sum(
        f, axis=-1)**2
    return divideWithZero(num_, denom_)


def spectral_variation(wts, samplingfrequency):
    f, fmag = calc_fft(wts, samplingfrequency)

    sum1 = np.sum(fmag[..., :-1] * fmag[..., 1:], axis=-1)
    sum2 = np.sum(fmag[..., 1:]**2, axis=-1)
    sum3 = np.sum(fmag[..., :-1]**2, axis=-1)

    return 1 - divideWithZero(sum1, ((sum2**0.5) * (sum3**0.5)))


def spectral_maxpeaks(wts, samplingfrequency):
    f, fmag = calc_fft(wts, samplingfrequency)
    return maxpeaks(fmag)


def spectral_roll_off(wts, samplingfrequency):
    f, fmag = calc_fft(wts, samplingfrequency)
    cum_fmag = np.cumsum(fmag, axis=-1)
    value = matchLastDimByRepeat(0.95 * np.sum(fmag, axis=-1), cum_fmag)
    ind_mag = np.argmax(np.array(np.asarray(cum_fmag > value)), axis=-1)
    ind_mag = np.expand_dims(ind_mag, axis=-1)
    return np.squeeze(np.take(f, ind_mag), axis=-1)


def spectral_roll_on(wts, samplingfrequency):
    f, fmag = calc_fft(wts, samplingfrequency)
    cum_fmag = np.cumsum(fmag, axis=-1)
    value = matchLastDimByRepeat(0.05 * np.sum(fmag, axis=-1), cum_fmag)
    ind_mag = np.argmax(np.array(np.asarray(cum_fmag >= value)), axis=-1)
    ind_mag = np.expand_dims(ind_mag, axis=-1)
    return np.squeeze(np.take(f, ind_mag), axis=-1)


def spectral_(wts, samplingfrequency):
    f, fmag = calc_fft(wts, samplingfrequency)
    return maxpeaks(fmag)


def human_range_energy(wts, samplingfrequency):
    f, fmag = calc_fft(wts, samplingfrequency)

    allenergy = np.sum(fmag**2, axis=-1)

    hr_energy = np.sum(
        fmag[...,
             np.argmin(np.abs(0.6 -
                              f[..., :])):np.argmin(np.abs(2.5 -
                                                           f[..., :]))]**2,
        axis=-1)

    return divideWithZero(hr_energy, allenergy)


def spectral_entropy(wts, samplingfrequency):
    # TODO: this norm is copied form original, but feels weird, check if necessary
    sig = wts - np.expand_dims(np.mean(wts, axis=-1), axis=-1)
    f, fmag = calc_fft(sig, samplingfrequency)

    power = fmag**2
    prob = np.divide(power, matchLastDimByRepeat(np.sum(power, axis=-1),
                                                 power))

    return __entropy(prob)


# === Multiple out ====================================================================================================


def fft_mean_coeff(wts, samplingfrequency, nfreq: int = 256):
    # preserves original behavior
    # assume all last axis' length to be the same
    nfreq = min(nfreq, np.ma.size(wts, axis=-1) // 2 + 1)

    return np.mean(scipy.signal.spectrogram(wts,
                                            samplingfrequency,
                                            nperseg=nfreq * 2 - 2,
                                            axis=-1)[2],
                   axis=-1)

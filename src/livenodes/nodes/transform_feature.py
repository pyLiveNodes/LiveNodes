import numpy as np
from inspect import signature

from livenodes.core.node import Node

### File mostly copy pasted from my mkr libaray (yh)
import tsfel.feature_extraction.features as tsfel

from .features.base import BaseTransformer_eager, FeatureUnion
from . import features as mkr_features

from . import local_registry


class SingleChannelFeature(BaseTransformer_eager):

    def __init__(self, fn, fnParams={}):
        self.fn = fn
        self.fnParams = fnParams

    def transformSingleChannelTS(self, ts):
        return np.array([self.fn(window, **self.fnParams) for window in ts])

    def transform(self, wts):
        return list(map(self.transformSingleChannelTS, wts))


class MultiChannelFeature(BaseTransformer_eager):

    def __init__(self, fn, fnParams={}):
        self.fn = fn
        self.fnParams = fnParams

    def transform(self, wts):
        return self.fn(wts, **self.fnParams)


class MultipleWrapper(BaseTransformer_eager):

    def __init__(self, estimator: BaseTransformer_eager):
        self.estimator = estimator

    def transform(self, wts):
        res = np.array(self.estimator.transform(wts))
        if len(
                res.shape
        ) == 2:  # -> the feature returned an array on each channel for each window
            self.dimensions_ = np.ma.size(res, axis=-1)
            return np.hstack(res.transpose(2, 0, 1))
        elif len(
                res.shape
        ) == 1:  # -> the feature returned a single value on each channel for each window
            self.dimensions_ = 1
            return res


@local_registry.register
class Transform_feature(Node):
    channels_in = ['Data', "Channel Names"]
    channels_out = ['Data', 'Channel Names']

    category = "Transform"
    description = ""

    example_init = {"name": "Name"}

    def __init__(self,
                 name="Features",
                 features=["calc_mean"],
                 feature_args={},
                 **kwargs):
        super().__init__(name, **kwargs)

        self.features = features
        self.feature_args = feature_args

        self.featureList = []
        for f_name in features:
            if f_name.startswith('tsfel:'):
                ftfn = getattr(tsfel, f_name[len('tsfel:'):])
                ftTransformer = SingleChannelFeature
            else:
                ftfn = getattr(mkr_features, f_name)
                ftTransformer = MultiChannelFeature

            ftfnParams = signature(ftfn).parameters
            ftArgs = {
                key: feature_args[key]
                for key in feature_args
                if key in ftfnParams and not key == 'wts'
            }

            self.featureList.append(
                MultipleWrapper(estimator=ftTransformer(ftfn, ftArgs)))

        self._union = FeatureUnion(self.featureList,
                                   featureNames=self.features)
        # self._union = FeatureUnion(self.featureList, featureNames=self.features, **self.unionParams)

        self.channel_names = None
        self.channels = []

    def _settings(self):
        return {\
            "features": self.features,
            "feature_args": self.feature_args
        }

    def _should_process(self, data=None, channel_names=None):
        return data is not None and \
            (self.channel_names is not None or channel_names is not None)

    # input shape: (batch/file, time, channel)
    def process(self, data, channel_names=None, **kwargs):
        if channel_names is not None:
            self.channel_names = channel_names

        # TODO: update the union stuff etc to not expect a tuple as input
        # TODO: update this to not expect it to be wrapped in a list
        # TODO: update this to not use a map anymore
        # TODO: currently ft.transform is called twice, as the dimensions_ will otherwise not be set -> most of the time we do double the work for no benefit
        # data, channels = self._union.transform((data_frame, self.channel_names))

        # the union implementation is from mkr and expects (batch, channel, time)
        fts, channels = self._union.transform((np.array(data).transpose(
            (0, 2, 1)), self.channel_names))

        # as we've folded the original time axis into the features, let's insert it with size one, to fulfill the (batch, time, channel) expectation
        # STOPPED HERE: TODO: rething the insertion as well as the channels put out by window. As the current idea doens't make much sense for normalization, as we would normalize on sequences of length 1... or should we normalize over batches? that feels quite wrong tho...
        # -> nvm: the norm is a running norm anyway, ie updates with every frame.
        # -> still makes sense to consider, but is less pressing
        res = np.expand_dims(np.array(list(fts)), axis=1)
        self._emit_data(res)

        if set(self.channels) != set(channels):
            self.channels = channels
            self._emit_data(channels, channel="Channel Names")

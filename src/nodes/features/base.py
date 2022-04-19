from sklearn.base import BaseEstimator, TransformerMixin, clone
import numpy as np
from copy import copy
import sklearn.pipeline as pipeline
from abc import ABC, abstractmethod

import typing as tp


class BaseTransformer_lazy(ABC, BaseEstimator, TransformerMixin):

    def fit(self, X: tp.Iterable, y) -> 'BaseTransformer_lazy':
        """Implements standard fit function from Sklearn

        As we often don't need it, it is just empty.

        Returns: self

        """
        return self

    # this does not work, as in this particular case O would need to be bound to I
    # @abstractmethod
    def transformTS(self, ts):
        """Transform a time series

        Usually this will be called by the Sklearn standard function :py:meth:`~transformers.base.BaseTransformer_lazy.transform`.

        Args:
            ts: The time series to transform

        Returns:
            The transformed series
        """
        pass

    def transform(self, session: tp.Iterable) -> tp.Iterable:
        """Implements standard transform function from Sklearn

        This is a lazy transformer, therfore the transformation is returned as map object and each item is only computed as needed.

        As this transforms an iterable of time series data, the transformation will mostly be forwarded to :py:meth:`~transformers.base.BaseTransformer_lazy.transformTS`.

        Args:
            sessionterable of time series

        Returns:
            A map object of transformed timeseries
        """
        session, columns = session
        return map(self.transformTS, session), columns


class BaseTransformer_eager(ABC, BaseEstimator, TransformerMixin):

    def fit(self, X: tp.Iterable, y) -> 'BaseTransformer_eager':
        """Implements standard fit function from Sklearn

        As we often don't need it, it is just empty.

        Returns: self

        """
        return self

    # this does not work, as in this particular case O would need to be bound to I
    # @abstractmethod

    def transformTS(self, ts):
        """Transform a time series

        Usually this will be called by the Sklearn standard function :py:meth:`~transformers.base.BaseTransformer_eager.transform`.

        Args:
            ts: The time series to transform

        Returns:
            The transformed series
        """
        pass

    def transform(self, session: tp.Iterable) -> tp.List:
        """Implements standard transform function from Sklearn

        As this transforms an iterable of time series data, the transformation will mostly be forwarded to :py:meth:`~transformers.base.BaseTransformer_eager.transformTS`.

        .. note::

            This is a eager transformer. This means all transformations are computed directly and require the full memory as well as the necessary processing power instantly.

        Args:
            sessionterable of time series

        Returns:
            An iterable of transformed timeseries
        """
        # Note: please be careful when considering to make this an numpy array
        # Please consider, that numpy would then convert the featuresequence to a list of featurevectors when calling transform on the ToMultiChannelFeatureSequence Transformer
        session, columns = session
        return list(map(self.transformTS, session)), columns


class CalcPipe(BaseTransformer_eager):
    """ Used to flush a sklearn pipeline and calculate all accumulated maps
    this is usefull if the next pipeline step does not work well with iterables like maps
    """

    def transform(self, session):
        return list(session[0]), session[1]


import traceback


class Flatten(BaseTransformer_eager):

    def transform(self, session):
        session, columns = session
        return np.vstack(session), columns

    # yeah not really what was meant, but works...
    def fit_transform(self, session, target):
        d, col = session
        return (np.vstack(d), col), np.hstack(target)


def first_double(iterable):
    first = next(iterable)
    yield first
    yield first
    for x in iterable:
        yield x


def batch_generator(itr, step):
    tmp = []
    for i, elem in enumerate(itr):
        tmp.append(elem)
        if (i + 1) % step == 0:
            yield tmp
            tmp = []
    if len(tmp) > 0:
        yield tmp


class FeatureUnion(BaseTransformer_lazy):

    def __init__(self,
                 featureInstances: tp.List[BaseEstimator],
                 featureNames=[],
                 safe=True,
                 batch_size=50,
                 **kwargs):
        """Time series compatible version of Sklearns FeatureUnion

        Sklearns Feature union does not work well with time series data, as it internally uses a hstack to concatenate the returned features.
        Therefore, this wrapper uses a Sklearn feature union on each time series.
        The assumption for this to work is, that no feature requires knowledge over the previous or following window.

        Example:
            If the original time series has the dimensions (440, nrSamples, 19) and there are two features calculated
            It returns (880, nrSamples, 19) instead of (440, nrSamples, 38) as would be done by sklearns union

        Args:
            BaseTransformer_lazy ([type]): [description]
            featureInstances ([type]): [description]
            unionParams ([type], optional): [description]. Defaults to {}.
        """
        self.featureInstances = featureInstances
        self.featureNames = featureNames
        self.batch_size = batch_size
        self.safe = safe
        self.unionParams = kwargs

    def transformTS(self, ts):
        return pipeline.make_union(*self.featureInstances,
                                   **self.unionParams).transform(ts)
        # there isn't really a reason to use pipeline here, as the n_jobs param is used in the pipeline this is injected in and therefore, cannot be taken advantage of here...

    # TODO: re-work this batch approach to be safe and default
    # Promises ft calc speedups up to max(batch_size, nr windows in seq), but effectively more around a tenth of the original time eg if orig was 1min25 new is 12s (calc on full shar with roughly 20 fully vectorized features)
    def transform_mapper(self, session):
        raise Exception(
            'Transform Mapper not implemented to standard'
        )  # <- remove for perf estimation, but don't use in production!
        # problems:
        #         1. code assumes 3dim arrays!!! -> might break code
        #         2. code assume features are independent of windows (should hold anyway, but this actually leads to false results if violated)

        for batch in batch_generator(session, self.batch_size):
            slc = np.concatenate(batch, axis=0)
            tmp = np.concatenate(
                [ft.transform(np.array(slc)) for ft in self.featureInstances],
                axis=1)
            res = []
            idx = 0
            for x in batch:
                res.append(tmp[idx:idx + x.shape[0]])
                idx += x.shape[0]

            for i in range(len(res)):
                yield (res)

    def transform(self, session: tp.Iterable) -> tp.List:
        session, columns = session

        # figure out which features have returned more than one channel per input channel
        features = []

        if type(session) == map:
            # TODO: check if this actually worked or if the first instance is now missing
            # -> did so, is fine
            session = first_double(session)
            toTransform = next(session)
        else:
            toTransform = session[0]

        for i, ft in enumerate(self.featureInstances):
            ft.transform(
                toTransform
            )  # required to access the number of dimensions of this feature
            if ft.dimensions_ is not None and ft.dimensions_ > 1:
                for j in range(ft.dimensions_):
                    features.append(f"{self.featureNames[i]}__nr_{j}")
            else:
                features.append(self.featureNames[i])

        out_cols = [
            f"{column}__{feature}" for feature in features
            for column in columns
        ]
        if self.safe:
            return map(self.transformTS, session), out_cols
        else:
            # TODO: see above this uses several assupmtions, that make the usage a lot faster, but also very prone to errors and wrong calculations, use with caution
            return self.transform_mapper(session), out_cols


class NonSeriesWrapper(BaseTransformer_lazy):

    def __init__(self, estimator: BaseEstimator):
        """Simple wrapper to make vector estimators "capable" of time series modelling

        This uses two assumptions:
        1. The input data can be concatenated into a single matrix
        2. Transform can be called several times on the estimator (ie the transform function is not stateful)

        .. note ::

            Most vector based estimators do not make a good fit for time series modelling.
            As they will assume the vectors in a time series to be independent, which they are not.

        Args:
            estimator: The estimator to be wrapped for time series data
        """
        self.estimator = estimator

    def fit(self, session: tp.Iterable, targets: tp.Iterable) -> BaseEstimator:
        """Fits the wrapped estimator

        Concatentes the session data into a single numpy data matrix and then fits the passed estimator with it.

        Args:
            session: Data (nr time series, nr samples, nr channels) to be fitted
            targets: List of targets (nr time series, nr samples)

        Returns:
            Fitted estimator
        """
        session, columns = session
        self.estimator_ = clone(self.estimator)
        print('fit')

        # the usage of list is necessary for this and the previous step to be lazy, as concatenate, cannot deal with map objects
        X_ = np.concatenate(list(session), axis=0)
        y_ = np.concatenate(targets, axis=0)
        self.estimator_.fit(X_, y_)

        return self

    def transformTS(self, ts):
        """Transform time series as if it was a list of independent vectors

        Args:
            ts: Time series to be transformed

        Returns:
            Transformed time series
        """
        return self.estimator_.transform(ts)

    def transform(self, session: tp.Iterable):
        print('transform')
        session, columns = session
        return map(self.transformTS, session), columns


class InjectColumnsIntoPipeline(BaseTransformer_lazy):

    def __init__(self, columns=[]):
        self.columns = columns

    def transform(self, session: tp.Iterable) -> tp.List:
        return session, self.columns


class RemoveColumnsFromPipeline(BaseTransformer_lazy):

    def transform(self, session: tp.Iterable) -> tp.List:
        return session[0]


class ToType(BaseTransformer_lazy):

    def __init__(self, toType='float16'):
        self.toType = toType

    def transformTS(self, wts: tp.Iterable) -> tp.List:
        if self.toType is not None:
            return np.array(wts).astype(self.toType)
        return wts

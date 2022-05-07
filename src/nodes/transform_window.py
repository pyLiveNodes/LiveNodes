import numpy as np
from core.node import Node


class Transform_window(Node):
    channels_in = ['Data']
    channels_out = ['Data']

    category = "Transform"
    description = ""

    example_init = {            
        "length": 100,
        "overlap": 0.0,
        "name": "Name",
        "concat_batches": True
    }

    def __init__(self,
                 length,
                 overlap,
                 concat_batches=True,
                 name="Window",
                 **kwargs):
        super().__init__(name=name, **kwargs)

        self.length = length
        self.overlap = overlap
        self.stepsize = length - overlap
        # mostly will be set to true, only if you want to have more control by sending in whole files, this might make sense to set to false
        self.concat_batches = concat_batches

        self.buffer = np.array([])
        self.ctrs = {}

        # self.storage = {}

    def _settings(self):
        return {\
            "length": self.length,
            "overlap": self.overlap,
            "name": self.name,
            "concat_batches": self.concat_batches
           }

    # def discard_previous_tick(self, ctr):
    #     return False

    # def _retrieve_current_data(self, ctr):
    #     # TODO: maybe there is a version where it makes sense to take the clock into account (seems that would be more robust...)?
    #     # This kinda only works, as the function is ever only called once atm...
    #     # -> self storage helps against multiple calls, but not against out of order calls...
    #     if not ctr in self.storage:
    #         self.storage[ctr] = self._received_data['Data'].queue.get()[1]

    #     return {
    #         # as we have only one input that may be connected and this function is only ever called if _process is called, we can this this way
    #         # TODO: test the heck out of this and the clock system! This still feels hacky
    #         # TODO: we currently are assuming, that the item we are getting here is also the last one put into the queue....
    #         'data': self.storage[ctr]
    #     }

    # from: https://gist.github.com/nils-werner/9d321441006b112a4b116a8387c2280c
    def __sliding_window(self, data, size, stepsize=1, axis=-1, copy=True):
        """
        Calculate a sliding window over a signal
        Parameters
        ----------
        data : numpy array
            The array to be slided over.
        size : int
            The sliding window size
        stepsize : int
            The sliding window stepsize. Defaults to 1.
        axis : int
            The axis to slide over. Defaults to the last axis.
        copy : bool
            Return strided array as copy to avoid sideffects when manipulating the
            output array.
        Returns
        -------
        data : numpy array
            A matrix where row in last dimension consists of one instance
            of the sliding window.
        Notes
        -----
        - Be wary of setting `copy` to `False` as undesired sideffects with the
        output values may occurr.
        Examples
        --------
        >>> a = numpy.array([1, 2, 3, 4, 5])
        >>> sliding_window(a, size=3)
        array([[1, 2, 3],
            [2, 3, 4],
            [3, 4, 5]])
        >>> sliding_window(a, size=3, stepsize=2)
        array([[1, 2, 3],
            [3, 4, 5]])
        See Also
        --------
        pieces : Calculate number of pieces available by sliding
        """
        if axis >= data.ndim:
            raise ValueError(f"Axis {axis} out of range for dim {data.ndim}")

        if stepsize < 1:
            raise ValueError("Stepsize may not be zero or negative")

        if size > data.shape[axis]:
            raise ValueError(
                f"Sliding window size may not exceed size of selected axis. got: {size}, but length is: {data.shape[axis]}"
            )

        shape = list(data.shape)
        shape[axis] = np.floor(data.shape[axis] / stepsize - size / stepsize +
                               1).astype(int)
        shape.append(size)

        strides = list(data.strides)
        strides[axis] *= stepsize
        strides.append(data.strides[axis])

        strided = np.lib.stride_tricks.as_strided(data,
                                                  shape=shape,
                                                  strides=strides)

        if copy:
            return strided.copy()
        return strided

    # input shape: (batch/file, time, channel)
    # if concat: make (batch/file * time, channel) and then window
    # otherwise: window over all batches
    def process(self, data, _ctr, **kwargs):
        d = np.array(data)

        if self.concat_batches:
            d = np.vstack(d)

            if self.buffer.size == 0:
                self.buffer = d
            else:
                self.buffer = np.vstack([self.buffer, d])

            # to_window = np.vstack(self.buffer)
            to_window = self.buffer
            self.ctrs[to_window.shape[0]] = _ctr

            if to_window.shape[0] >= self.length:
                res = self.__sliding_window(to_window,
                                            size=self.length,
                                            stepsize=self.stepsize,
                                            axis=0,
                                            copy=True)
                res = res.transpose((0, 2, 1))
                # self.debug(res[0,:,0])
                used_samples = self.length + (res.shape[0] -
                                              1) * (self.length - self.overlap)
                # used_samples = int(res.size / res.shape[1]) -> this is only true if stepsize is equals to length!
                self.buffer = self.buffer[used_samples:]
                first_ctr = self.ctrs[min(self.ctrs.keys())]
                self.ctrs = {
                    key: val
                    for key, val in self.ctrs.items() if val >= used_samples
                }
                self._emit_data(res, ctr=first_ctr)
        else:
            # self.buffer.extend(data)
            raise NotImplementedError(
                'No (offline) file based routine implemented yet for windowing.'
            )

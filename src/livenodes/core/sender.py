from .node import Node, Location, Clock


class Sender(Node):
    """
    Loops the process function until it returns false, indicating that no more data is to be sent
    """

    channels_in = []  # must be empty!

    def __init__(self,
                 name,
                 block=False,
                 compute_on=Location.THREAD,
                 should_time=False):
        super().__init__(name, compute_on, should_time)

        if not block and compute_on == Location.SAME:
            # TODO: consider how to not block this in Location.Same?
            raise ValueError('Block cannot be false if location=same')

        # TODO: also consider if this is better suited as parameter to start?
        self.block = block

        self._clock = Clock(node=self, should_time=should_time)
        self._ctr = self._clock.ctr
        self._emit_ctr_fallback = 0

    def _node_settings(self):
        return dict({"block": self.block}, **super()._node_settings())

    def __init_subclass__(cls):
        super().__init_subclass__()
        if len(cls.channels_in) > 0:
            # This is a design choice. Technically this might even be possible, but at the time of writing i do not forsee a usefull case.
            raise ValueError('Sender nodes cannot have input')

    def _run(self):
        """
        should be implemented instead of the standard process function
        should be a generator
        """
        yield False

    def _emit_data(self, data, channel="Data", ctr=None):
        self._emit_ctr_fallback += 1
        return super()._emit_data(data, channel, ctr)

    def _on_runner(self):
        # everytime next(runner) has been called, this should be called
        # TODO: maybe wrap the self._run() into a generator, that calls this automatically...
        # self.debug('Next(Runner) was called')
        if self._emit_ctr_fallback > 0:
            # self.debug('Putting on queue', str(self), self._ctr)
            self._clocks.register(str(self), self._ctr)
            # self.debug('Put on queue')
            self._ctr = self._clock.tick()
        else:
            raise Exception(
                f'Runner did not emit data, yet said it would do so in the previous run. Please check your implementation of {self}.'
            )
        self._emit_ctr_fallback = 0
        # self.debug('Next(Runner) returned')

    def _process_on_proc(self):
        self.info('Started subprocess')
        runner = self._run()
        try:
            # as long as we do not receive a termination signal and there is data, we will send data
            while not self._acquire_lock(
                    self._subprocess_info['termination_lock'],
                    block=False) and next(runner):
                self._on_runner()

        except StopIteration:
            self.warn(
                'Iterator returned without passing false first. Assuming everything is fine.'
            )

        self.info('Reached end of run')
        # this still means we send data, before the return, just that after now no new data will be sent
        self._on_runner()
        self.info('Finished subprocess', self._ctr)

    def start_node(self, children=True, join=False):
        super().start_node(children, join=False)

        if self.compute_on in [Location.PROCESS, Location.THREAD
                               ] and self.block:
            self._subprocess_info['process'].join()
        elif self.compute_on in [Location.SAME]:
            # iterate until the generator that is run() returns false, ie no further data is to be processed
            try:
                runner = self._run()
                while next(runner):
                    self._on_runner()
            except StopIteration:
                self.warn(
                    'Iterator returned without passing false first. Assuming everything is fine.'
                )
            self.info('Reached end of run')
            # this still means we send data, before the return, just that after now no new data will be sent
            self._on_runner()

        if join:
            self._join()
        else:
            self._clocks.set_passthrough()

    def _join(self):
        if not self.block:
            raise Exception(
                'Cannot join non-blocking senders as we have no way of knowing when they are finished atm'
            )
            # theoretically we can still use the ret false concept from the senders ie yield False indicates finish
        return super()._join()

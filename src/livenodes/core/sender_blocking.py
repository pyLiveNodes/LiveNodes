from .node import Location, Clock
from .sender import Sender

class BlockingSender(Sender):

    # TODO: check if the block parameter even does anything
    def __init__(self,
                 name,
                 block=False,
                 compute_on=Location.PROCESS,
                 should_time=False):
        super().__init__(name, block, compute_on, should_time)

        self._clock = Clock(node=self, should_time=should_time)
        self._ctr = self._clock.ctr

    def _emit_data(self, data, channel="Data"):
        super()._emit_data(data, channel)
        # as we are a blocking sender / a sensore everytime we emit a sample, we advance our clock
        if channel == "Data":
            self._clocks.register(str(self), self._ctr)
            self._ctr = self._clock.tick()

    def _process_on_proc(self):
        self.info('Started subprocess')
        try:
            self._onstart()
        except KeyboardInterrupt:
            # TODO: this seems to be never called
            self.info('Received Termination Signal')
            self._onstop()
        self.info('Finished subprocess')

    def start(self, children=True, join=False):
        super().start(children, join=False)

        if self.compute_on in [Location.PROCESS, Location.THREAD]:
            if self.block:
                self._subprocess_info['process'].join()
        elif self.compute_on in [Location.SAME]:
            self._onstart()

        if join:
            self._join()
        else: 
            self._clocks.set_passthrough()

    def stop(self, children=True):
        # first stop self, so that non-existing children don't receive inputs
        if self._running == True:  # the node might be child to multiple parents, but we just want to stop once
            self._running = False

            if self.compute_on in [Location.SAME, Location.THREAD]:
                self._onstop()
            elif self.compute_on in [Location.PROCESS]:
                self._subprocess_info['process'].kill()

        # now stop children
        if children:
            for con in self.output_connections:
                con._receiving_node.stop()

from livenodes.port import Port
from .node import Location
from .sender import Sender


class BlockingSender(Sender):

    # TODO: check if the block parameter even does anything
    def __init__(self,
                 name,
                 block=False,
                 compute_on=Location.PROCESS):
        super().__init__(name, block, compute_on)

        if compute_on != Location.PROCESS:
            raise NotImplementedError('Other than process is not implemented at this point')
            # TODO: not exactly true, but there defenitely is a bug in the other implementations!
            # ie, in the RIoT example from semi-online, with compute=thread claims to have stopped, but continues to send data and does not stop its children
            # which is mainly due to the fact, that it just calls _onstop, which is not implemented and just passed in node._onstop (line 887)

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

    def start_node(self, children=True, join=False):
        super().start_node(children, join=False)

        if self.compute_on in [Location.PROCESS, Location.THREAD]:
            if self.block:
                self._subprocess_info['process'].join()
        elif self.compute_on in [Location.SAME]:
            self._onstart()

        if join:
            self._join()
        else:
            self._clocks.set_passthrough(self)

    def stop_node(self, children=True):
        # first stop self, so that non-existing children don't receive inputs
        if self._running == True:  # the node might be child to multiple parents, but we just want to stop once
            self.info('Stopping')
            self._running = False

            if self.compute_on in [Location.SAME, Location.THREAD]:
                self._onstop()
            elif self.compute_on in [Location.PROCESS]:
                self._subprocess_info['process'].kill()
            self.info('Stopped')

            # now stop children
            if children:
                for con in self.output_connections:
                    con._recv_node.stop_node()

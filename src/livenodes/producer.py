import asyncio
from functools import partial
from this import d
from .node import Node, Location
from .components.utils.clock import Clock

from typing import NamedTuple
class Ports_empty(NamedTuple):
    pass

class Producer(Node):
    """
    Executes onstart and waits for it to return / indicate no more data is remaining.
    Then onstop is executed and 
    """

    ports_in = Ports_empty() # must be empty!

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._clock = Clock(node_id=self)
        self._ctr = self._clock.ctr # set as is used in Node! (yes, we should rework this)
        self._emit_ctr_fallback = 0

        self._running = False

    def __init_subclass__(cls):
        super().__init_subclass__()
        if len(cls.ports_in) > 0:
            # This is a design choice. Technically this might even be possible, but at the time of writing i do not forsee a usefull case.
            raise ValueError('Sender nodes cannot have input')

    def _run(self):
        """
        legacy and convenience function
        """
        yield False

    async def _async_onstart(self):
        """
        Main function producing data and calling _emit_data.
        Once it returns the node system assumes no furhter data will be send and communicates this to all following nodes

        Per default _onstart assumes _run returns a generator and loops it until it returns false.
        _onstart may be overwritten by sender, but has to call _emit_data and must call _clock.tick() once a cycle of data is complete, e.g. the pair of annotation and data is sent
        
        # Note to future self: the clock.tick() requirement might have been removed if _emit_data was dropped in favor of returns
        """ 

        # Todo: change this to just register a recursive sender task as well

        # create generator
        runner = self._run()
        # wrap in call user fn
        fn = partial(self._call_user_fn_process, next, "runner")

        # finish either if no data is present anymore or parent told us to stop (via stop() -> _onstop())
        while fn(runner) and self._running:
            if self._emit_ctr_fallback > 0:
                # self.debug('Putting on queue', str(self), self._ctr)
                # self.debug('Put on queue')
                self._ctr = self._clock.tick()
            else:
                raise Exception(
                    f'Runner did not emit data, yet said it would do so in the previous run. Please check your implementation of {self}.'
                )
            self._emit_ctr_fallback = 0
            
            # allow others to chime in
            await asyncio.sleep(0)

        self._finish()

    def _onstop(self):
        self._running = False

    def _onstart(self):
        self._running = True

        # mmh, wouldn't this fit more into a on_ready() call?
        loop = asyncio.get_event_loop()
        loop.create_task(self._async_onstart())

    def _emit_data(self, data, channel=None, ctr=None):
        self._emit_ctr_fallback += 1
        return super()._emit_data(data, channel, ctr)


import asyncio
from functools import partial
import traceback
from .producer import Producer

class Producer_async(Producer, abstract_class=True):
    
    async def _async_run(self):
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

        # Note on timing: 
        # this node cannot be timed at the moment, as i'm not sure how the Time_Per_Call and Time_Between_Calls should be handled in the async case...
        async def _anext(ait):
            try:
                return await ait.__anext__(), True
            except StopAsyncIteration:
                return None, False
            except Exception as e:
                self.error(f'failed to execute _async_run')
                self.error(e)
                self.error(traceback.format_exc())
                return None, False

        # create generator
        runner = self._async_run()
            
        # finish either if no data is present anymore or parent told us to stop (via stop() -> _onstop())
        while self._running:
            emit_data, empty = await _anext(runner)
             
            if empty:
                for key, val in emit_data.items():
                    self._emit_data(data=val, channel=key)
                self._ctr = self._clock.tick()
            else:
                # Received no data from the generator, thus stopping the production :-) 
                self._onstop()

            self._report(node=self)            
            # allow others to chime in
            await asyncio.sleep(0)

        self._finish()

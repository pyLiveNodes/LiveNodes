import asyncio
import traceback
from .producer import Producer
import threading as th
import aioprocessing

class Producer_Blocking(Producer, abstract_class=True):
    """
    Executes onstart and waits for it to return / indicate no more data is remaining.
    Then onstop is executed and 
    """

    def __init__(self, name="Name", should_time=False, compute_on="", **kwargs):
        super().__init__(name, should_time, compute_on, **kwargs)

        # main thread
        self.subprocess = None

        # both threads
        self.stop_event = th.Event()
        self.finished_event = th.Event()
        self.msgs = aioprocessing.AioQueue()


    # sub_thread
    def _blocking_onstart(self):
        """
        Run blocking producer in here.
        Data should be put in the self.msgs queue
        Once the stop_event is set this function must (!) unblock and return

        It may do so earlier as well, but should call self._finish then? 
            -> this doesn't make sense as that would be the wrong thread
            -> where/should it be called then?
        """
        pass

    def _subprocess(self):
        try:
            self._blocking_onstart()
        except Exception as e:
            self.error(f'failed to execute subprocess for {str(self)}')
            self.error(e)
            self.error(traceback.format_exc())
    
    async def _async_onstart(self):
        port_lookup = self.ports_out._asdict()
        # print(port_lookup)
        while not self.stop_event.is_set():
            try:
                item, port_name, tick = await self.msgs.coro_get()
                if item is None:
                    self.info(f'Producer {self} received None, stopping')
                    self.stop_event.set()
                else:
                    self._emit_data(item, channel=port_lookup[port_name])
                    if tick:
                        self._ctr = self._clock.tick()
                self._report()
            except Exception as e:
                self.error(e)
                self.error(traceback.format_exc())

        self._finish()  
        self.finished_event.set()
    
    # main thread (interfaced by node system)
    def _onstart(self):
        # daemon => kill once main thread is done, see: https://stackoverflow.com/questions/190010/daemon-threads-explanation
        self.subprocess = th.Thread(target=self._blocking_onstart, daemon=True, args=(self.stop_event,))
        self.subprocess.start()

        self.stop_event.clear()
        self.finished_event.clear()

        loop = asyncio.get_event_loop()
        loop.create_task(self._async_onstart())



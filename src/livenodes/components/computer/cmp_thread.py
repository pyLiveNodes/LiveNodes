
import asyncio
import threading as th

from livenodes.components.node_logger import Logger

# TODO: is this also possibly without creating a new thread, ie inside of main thread? 
# i'm guessing no, as then the start likely does not return and then cannot be stopped by hand, but only if it returns by itself

class Processor_threads(Logger):
    def __init__(self, nodes, location, bridges) -> None:
        super().__init__()
        # -- both threads
        # indicates that the subprocess is ready
        self.ready_event = th.Event() 
        # indicates that the readied nodes should start sending data
        self.start_lock = th.Lock() 
        # indicates that the started nodes should stop sending data
        self.stop_lock = th.Lock() 
        # indicates that the thread should be closed without waiting on the nodes to finish
        self.close_lock = th.Lock() 
        # used for logging identification
        self.location = location

        # -- parent thread
        self.nodes = nodes
        self.bridges = bridges
        self.subprocess = None
        self.start_lock.acquire()
        self.stop_lock.acquire()
        self.close_lock.acquire()

        self.info(f'Creating Threading Computer with {len(self.nodes)} nodes.')

    def __str__(self) -> str:
        return f"CMP-TH:{self.location}"

    # parent thread
    def setup(self):
        self.info('Readying')

        self.subprocess = th.Thread(
                        target=self.start_subprocess,
                        args=(self.bridges,), name=str(self))
        self.subprocess.start()
        
        self.info('Waiting for worker to be ready')
        self.ready_event.wait(10)
        self.info('Worker ready, resuming')

    # parent thread
    def start(self):
        self.info('Starting')
        self.start_lock.release()

    # parent thread
    def join(self, timeout=None):
        """ used if the processing is nown to end"""
        self.info('Joining')
        self.subprocess.join(timeout)

    # parent thread
    def stop(self, timeout=0.1):
        """ used if the processing is nown to be endless"""

        self.info('Stopping')
        self.stop_lock.release()
        self.subprocess.join(timeout)
        self.info('Returning; thread finished: ', not self.subprocess.is_alive())

    # parent thread
    def close(self, timeout=0.1):
        self.info('Closing')
        self.close_lock.release()
        self.subprocess.join(timeout)
        if self.subprocess.is_alive():
            self.info('Timout reached, but still alive')
        # self.subprocess = None
    
    # parent thread
    def is_finished(self):
        return (self.subprocess is not None) and (not self.subprocess.is_alive())
        
    # worker thread
    def start_subprocess(self, bridges):
        self.info('Starting Thread')
        self.ready_event.set()

        def custom_exception_handler(loop, context):
            nonlocal self
            self.error(context)
            return loop.default_exception_handler(context)

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # TODO: this doesn't seem to do much?
        self.loop.set_exception_handler(custom_exception_handler)

        futures = []

        for node, bridges in zip(self.nodes, bridges):
            input_bridges, output_bridges = bridges['recv'], bridges['emit']
            futures.append(node.ready(input_endpoints=input_bridges, output_endpoints=output_bridges))

        self.start_lock.acquire()
        for node in self.nodes:
            node.start()

        self.onprocess_task = asyncio.gather(*futures)
        self.onprocess_task.add_done_callback(self.handle_finished)
        self.onstop_task = asyncio.gather(self.handle_stop())
        self.onclose_task = asyncio.gather(self.handle_close())

        # async def combined_tasks():
        #     try:
        #         await asyncio.gather(self.onprocess_task, self.onstop_task, self.onclose_task)
        #     except Exception as e:
        #         self.error(f'failed on one of the combined tasks in: {str(self)}')
        #         self.error(e)
        #         self.error(traceback.format_exc())

        # with the return_exceptions, we don't care how the processe
        self.loop.run_until_complete(asyncio.gather(self.onprocess_task, self.onstop_task, self.onclose_task, return_exceptions=True))

        # wrap up the asyncio event loop
        self.loop.stop()
        self.loop.close()

        self.info('Finished subprocess and returning')

    # worker thread
    def handle_finished(self, *args):
        self.info('All Tasks finished, aborting stop and close listeners')

        self.onstop_task.cancel()
        self.onclose_task.cancel()

    # worker thread
    async def handle_stop(self):

        # loop non-blockingly until we can acquire the stop lock
        while not self.stop_lock.acquire(timeout=0):
            await asyncio.sleep(0.001)
        
        self.info('Stopped called, stopping nodes')
        for node in self.nodes:
            node.stop()

    # worker thread
    async def handle_close(self):
        # loop non-blockingly until we can acquire the close/termination lock
        while not self.close_lock.acquire(timeout=0):
            await asyncio.sleep(0.001)
        
        # print('Closing running nodes')
        # for node in self.nodes:
        #     node.close()

        # give one last chance to all to finish
        # await asyncio.sleep(0)

        self.info('Closed called, stopping all remaining tasks')
        self.onprocess_task.cancel()


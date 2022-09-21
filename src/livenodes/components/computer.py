
import asyncio
import threading as th
import multiprocessing as mp

from livenodes.components.node_logger import Logger

# TODO: is this also possibly without creating a new thread, ie inside of main thread? 
# i'm guessing no, as then the start likely does not return and then cannot be stopped by hand, but only if it returns by itself

def resolve_computer(location):
    # TODO: :D
    return Processor_threading

def parse_location(location):
    host, port, process, thread = None, None, None, None
    
    splits = location.split(':')

    if len(splits) == 3:
        host, process, thread = splits
    elif (len(splits) == 4):
        host, port, process, thread = splits
    else:
        raise ValueError('Could not parse location', location)

    return host, port, process, thread

class Processor_threading(Logger):
    def __init__(self, nodes, location) -> None:
        super().__init__()
        # -- both threads
        # indicates that the readied nodes should start sending data
        self.start_lock = th.Lock() 
        # indicates that the started nodes should stop sending data
        self.stop_lock = th.Lock() 
        # indicates that the thread should be closed without waiting on the nodes to finish
        self.close_lock = th.Lock() 
        # used for logging identification
        self.location = location

        # -- main thread
        self.nodes = nodes
        self.subprocess = None
        self.start_lock.acquire()
        self.stop_lock.acquire()
        self.close_lock.acquire()

    def __str__(self) -> str:
        return f"Computer:{self.location}"

    # main thread
    def setup(self):
        self.info('Readying')
        self.subprocess = th.Thread(
                        target=self.start_subprocess)
        self.subprocess.start()

    # main thread
    def start(self):
        self.info('Starting')
        self.start_lock.release()

    # main thread
    def join(self):
        """ used if the processing is nown to end"""
        self.info('Joining')
        self.subprocess.join()

    # main thread
    def stop(self, timeout=0.1):
        """ used if the processing is nown to be endless"""

        self.info('Stopping')
        self.stop_lock.release()
        self.subprocess.join(timeout)
        self.info('Returning; subprocess finished: ', not self.subprocess.isAlive())

    # main thread
    def close(self, timeout=0.1):
        self.info('Closing')
        self.close_lock.release()
        self.subprocess.join(timeout)
        if self.subprocess.is_alive():
            self.info('Timout reached, but still alive')
        
    # worker thread
    def start_subprocess(self):
        self.info('Starting Subprocess')

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        futures = []

        for node in self.nodes:
            futures.append(node.ready())

        self.start_lock.acquire()

        for node in self.nodes:
            node.start()

        self.onprocess_task = asyncio.gather(*futures)
        self.onprocess_task.add_done_callback(self.handle_finished)
        self.onstop_task = asyncio.gather(self.handle_stop())
        self.onclose_task = asyncio.gather(self.handle_close())

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

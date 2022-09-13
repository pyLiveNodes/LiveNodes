
import asyncio
import threading as th
import multiprocessing as mp

# TODO: is this also possibly without creating a new thread, ie inside of main thread? 
# i'm guessing no, as then the start likely does not return and then cannot be stopped by hand, but only if it returns by itself

def resolve_computer(location):
    # TODO: :D
    return Processor_threading

class Processor_threading():
    def __init__(self, nodes) -> None:
        # -- both threads
        # indicates that the readied nodes should start sending data
        self.start_lock = th.Lock() 
        # indicates that the started nodes should stop sending data
        self.stop_lock = th.Lock() 
        # indicates that the thread should be closed without waiting on the nodes to finish
        self.close_lock = th.Lock() 

        # -- main thread
        self.nodes = nodes
        self.subprocess = None
        self.start_lock.acquire()
        self.stop_lock.acquire()
        self.close_lock.acquire()


    # main thread
    def setup(self):
        self.subprocess = th.Thread(
                        target=self.start_subprocess)
        self.subprocess.start()

    # main thread
    def start(self):
        self.start_lock.release()

    # main thread
    def join(self):
        """ used if the processing is nown to end"""
        self.subprocess.join()

    # main thread
    def stop(self, timeout=0.1):
        """ used if the processing is nown to be endless"""

        self.stop_lock.release()
        self.subprocess.join(timeout)
        print('Finished stopping')

    # main thread
    def close(self, timeout=0.1):
        print('Start stopping')
        self.close_lock.release()
        self.subprocess.join(timeout)
        if self.subprocess.is_alive():
            print('Timout triggerd, terminating thread')
        
    # worker thread
    def start_subprocess(self):
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
        print('finished and should return now')
        
        # wrap up the asyncio event loop
        self.loop.stop()
        self.loop.close()

    # worker thread
    def handle_finished(self, *args):
        self.onstop_task.cancel()
        self.onclose_task.cancel()

    # worker thread
    async def handle_stop(self):
        # loop non-blockingly until we can acquire the stop lock
        while not self.stop_lock.acquire(timeout=0):
            await asyncio.sleep(0.01)
        
        print('Stopping running nodes')
        for node in self.nodes:
            node.stop()

    # worker thread
    async def handle_close(self):
        # loop non-blockingly until we can acquire the close/termination lock
        while not self.close_lock.acquire(timeout=0):
            await asyncio.sleep(0.01)
        
        # print('Closing running nodes')
        # for node in self.nodes:
        #     node.close()

        # give one last chance to all to finish
        # await asyncio.sleep(0)

        print('Canceling everything that remains')
        self.onprocess_task.cancel()


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
        # both threads
        self.termination_lock = th.Lock()
        self.start_lock = th.Lock()

        # main thread
        self.nodes = nodes
        self.subprocess_handle = None
        self.termination_lock.acquire()
        self.start_lock.acquire()


    # main thread
    def setup(self):
        self.subprocess_handle = th.Thread(
                        target=self.start_subprocess)
        self.subprocess_handle.start()

    # main thread
    def start(self):
        self.start_lock.release()

    # main thread
    def stop(self, timeout=0):
        # we can probably handle termination more gracefully than aborting everything?
        print('Start stopping')
        if timeout > 0:
            self.termination_lock.release()
            print('joining')
            self.subprocess_handle.join(0.1)
            print('join done')
            if self.subprocess_handle.is_alive():
                print('Timout triggerd, terminating thread')
        else:
            self.subprocess_handle.join()
        print('Finished stopping')

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

        self.handle_abort_task = asyncio.gather(self.handle_stop())
        
        self.gather_task = asyncio.gather(*futures, return_exceptions=False)
        self.gather_task.add_done_callback(self.handle_finished)

        try:
            self.loop.run_until_complete(asyncio.gather(self.gather_task, self.handle_abort_task))
        except asyncio.CancelledError:
            # basically means we are finished now :-)
            pass
        print('finished and should return now')
    
    # worker thread
    def handle_finished(self, *args):
        print('Canceling handle_stop listener')
        self.handle_abort_task.cancel()

    # worker thread
    async def handle_stop(self):
        # loop non-blockingly until we can acquire the termination lock
        while not self.termination_lock.acquire(timeout=0):
            await asyncio.sleep(0.1)
        print('Canceling running tasks')
        # TODO: we can probably handle termination more gracefully than aborting everything?
        self.gather_task.cancel()

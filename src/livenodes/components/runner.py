
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

    def start(self):
        self.start_lock.release()

    # main thread
    def stop(self, force=False):
        # we can probably handle termination more gracefully than aborting everything?
        self.termination_lock.release()
        if force:
            self.subprocess_handle.join(1)
            self.subprocess_handle.terminate()
        else:
            self.subprocess_handle.join()


    # worker thread
    def start_subprocess(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # futures = [self.handle_stop()]
        futures = []

        for node in self.nodes:
            futures.append(node.ready())

        self.start_lock.acquire()

        for node in self.nodes:
            node.start()

        # we can probably handle termination more gracefully than aborting everything?
        # self.loop.run_until_complete([asyncio.wait(futures, return_when=asyncio.FIRST_EXCEPTION)])
        self.loop.run_until_complete(asyncio.wait(futures))

    # worker thread
    async def handle_stop(self):
        # todo: do this more elegantly -> any async await options?
        while True:
            if self.termination_lock.acquire(timeout=0.1):
                raise Exception('Termination order from parent.') 

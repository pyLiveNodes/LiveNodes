import asyncio
import threading as th
from livenodes.components.node_logger import Logger

class WorkerThread(Logger):
    def __init__(self, nodes, bridges, ready_event, start_lock, stop_lock, close_lock, location):
        super().__init__()
        self.nodes = nodes
        self.bridges = bridges
        self.ready_event = ready_event
        self.start_lock = start_lock
        self.stop_lock = stop_lock
        self.close_lock = close_lock
        self.location = location
        self.loop = None
        self.onprocess_task = None
        self.onstop_task = None
        self.onclose_task = None

    def start(self):
        self.info('Starting Thread')
        self.ready_event.set()

        def custom_exception_handler(loop, context):
            self.error(context)
            return loop.default_exception_handler(context)

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.set_exception_handler(custom_exception_handler)

        futures = []

        for node, bridges in zip(self.nodes, self.bridges):
            input_bridges, output_bridges = bridges['recv'], bridges['emit']
            futures.append(node.ready(input_endpoints=input_bridges, output_endpoints=output_bridges))

        self.start_lock.acquire()
        for node in self.nodes:
            node.start()

        self.onprocess_task = asyncio.gather(*futures)
        self.onprocess_task.add_done_callback(self.handle_finished)
        self.onstop_task = asyncio.gather(self.handle_stop())
        self.onclose_task = asyncio.gather(self.handle_close())

        self.loop.run_until_complete(asyncio.gather(self.onprocess_task, self.onstop_task, self.onclose_task, return_exceptions=True))

        self.loop.stop()
        self.loop.close()

        self.info('Finished subprocess and returning')

    def handle_finished(self, *args):
        self.info('All Tasks finished, aborting stop and close listeners')
        self.onstop_task.cancel()
        self.onclose_task.cancel()

    async def handle_stop(self):
        # loop non-blockingly until we can acquire the stop lock
        while not self.stop_lock.acquire(timeout=0):
            await asyncio.sleep(0.001)
        
        self.info('Stopped called, stopping nodes')
        for node in self.nodes:
            node.stop()

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


def start_subprocess(nodes, bridges, ready_event, start_lock, stop_lock, close_lock, location):
    worker = WorkerThread(
        nodes=nodes,
        bridges=bridges,
        ready_event=ready_event,
        start_lock=start_lock,
        stop_lock=stop_lock,
        close_lock=close_lock,
        location=location
    )
    worker.start()

class Processor_threads(Logger):
    def __init__(self, nodes, location, bridges) -> None:
        super().__init__()
        self.ready_event = th.Event()
        self.start_lock = th.Lock()
        self.stop_lock = th.Lock()
        self.close_lock = th.Lock()
        self.location = location
        self.nodes = nodes
        self.bridges = bridges
        self.subprocess = None
        self.start_lock.acquire()
        self.stop_lock.acquire()
        self.close_lock.acquire()

        self.info(f'Creating Threading Computer with {len(self.nodes)} nodes.')

    def __str__(self) -> str:
        return f"CMP-TH:{self.location}"

    def setup(self):
        self.info('Readying')
        self.subprocess = th.Thread(
            target=start_subprocess,
            args=(self.nodes, self.bridges, self.ready_event, self.start_lock, self.stop_lock, self.close_lock, self.location),
            name=str(self)
        )
        self.subprocess.start()
        self.info('Waiting for worker to be ready')
        self.ready_event.wait(10)
        self.info('Worker ready, resuming')

    def start(self):
        self.info('Starting')
        self.start_lock.release()

    def join(self, timeout=None):
        self.info('Joining')
        self.subprocess.join(timeout)

    def stop(self, timeout=0.1):
        self.info('Stopping')
        self.stop_lock.release()
        self.subprocess.join(timeout)
        self.info('Returning; thread finished: ', not self.subprocess.is_alive())

    def close(self, timeout=0.1):
        self.info('Closing')
        self.close_lock.release()
        self.subprocess.join(timeout)
        if self.subprocess.is_alive():
            self.info('Timeout reached, but still alive')

    def is_finished(self):
        return (self.subprocess is not None) and (not self.subprocess.is_alive())

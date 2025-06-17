import asyncio
from livenodes.components.node_logger import Logger

class Processor_local(Logger):
    def __init__(self, nodes, location, bridges) -> None:
        super().__init__()
        # used for logging identification
        self.location = location

        self.nodes = nodes
        self.bridges = bridges

        self.loop = None
        self.tasks = []

        self.info(f'Creating Threading Computer with {len(self.nodes)} nodes.')

    def __str__(self) -> str:
        return f"CMP-TH:{self.location}"

    def custom_exception_handler(self, loop, context):
        self.error(context)
        return loop.default_exception_handler(context)
    
    # parent thread
    def setup(self):
        self.info('Readying')

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # TODO: this doesn't seem to do much?
        self.loop.set_exception_handler(self.custom_exception_handler)
        
        self.tasks = [
            self.loop.create_task(node.ready(input_endpoints=recv,
                                            output_endpoints=emit))
            for node, (recv, emit) in zip(self.nodes, self.bridges)
        ]

    # parent thread
    def start(self):
        self.info('Starting')
        for node in self.nodes:
            node.start()

        # self.loop.create_task(self.onprocess_task)
        # now drive the loop until someone calls stop()
        self.info('Running loop')
        self.loop.run_forever()

    # parent thread
    def stop(self, timeout: float = 1.0):
        """Signal all nodes to stop and schedule loop.stop() after a grace period."""
        self.info(f'Stopping; will stop loop in {timeout}s')
        # 1) signal node stop inside event loop
        self.loop.call_soon_threadsafe(self._stop)
        # 2) schedule loop.stop after timeout
        self.loop.call_soon_threadsafe(lambda: self.loop.call_later(timeout, self.loop.stop))
        self.info('Stop signal and loop-stop scheduled')

    # parent thread
    def close(self):
        """Force-cancel any remaining tasks and close the event loop."""
        self.info('Closing')
        # cancel all unfinished tasks
        for task in self.tasks:
            if not task.done():
                self.loop.call_soon_threadsafe(task.cancel)
        # gather to let cancellations propagate
        self.loop.run_until_complete(
            asyncio.gather(*self.tasks, return_exceptions=True)
        )
        # shutdown any async generators
        self.loop.run_until_complete(self.loop.shutdown_asyncgens())
        # close the loop
        self.info('Finalizing close')
        self.loop.close()
        self.info(f'Returning; loop finished: {not self.loop.is_running()}')
        self.loop = None
    
    # parent thread
    def is_finished(self):
        return bool(self.tasks) and all(task.done() for task in self.tasks)
        
    # within loop
    def _stop(self):
        """Signal each node to wrap up; loop.stop is scheduled separately."""
        self.info('Stopping nodes')
        for node in self.nodes:
            node.stop()



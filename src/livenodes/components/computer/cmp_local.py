import threading as th
from .cmp_common import Processor_base
import asyncio
import logging
from logging.handlers import QueueHandler

def local_child_main(location, successor, successor_args,
                    ready_event, start_event, stop_event, close_event,
                    subprocess_log_queue, logger_name,
                    stop_timeout, close_timeout):
    """Child entrypoint for local (asyncio) processors."""
    logger = logging.getLogger(logger_name)
    if subprocess_log_queue:
        handler = QueueHandler(subprocess_log_queue)
        logger.addHandler(handler)
        # when using a queue handler, disable propagation to avoid duplicate logs
        logger.propagate = False
    else:
        # no queue for local processor: enable propagation so logs go to console
        logger.propagate = True
    
    nodes, bridges = successor_args

    # set up event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.set_exception_handler(lambda l, ctx: logger.error(ctx) or l.default_exception_handler(ctx))

    # schedule ready tasks
    tasks = [asyncio.ensure_future(
                  node.ready(input_endpoints=b['recv'], output_endpoints=b['emit']),
                  loop=loop)
             for node, b in zip(nodes, bridges)]
    logger.info('All Nodes ready')
    ready_event.set()

    # wait until start
    start_event.wait()
    logger.info('Starting Nodes')
    for node in nodes:
        node.start()
        
    # wait until either all tasks complete or external stop_event
    async def _run_until():
        stop_future = loop.run_in_executor(None, stop_event.wait)
        done, pending = await asyncio.wait(
            tasks + [stop_future], return_when=asyncio.FIRST_COMPLETED
        )
        all_done = all(t in done for t in tasks)
        if not all_done:
            # external stop: wait for close_event
            await loop.run_in_executor(None, close_event.wait)
            # request nodes to stop gracefully
            for node in nodes:
                try:
                    node.stop()
                except Exception:
                    logger.exception(f"Error stopping node {node}")
            # allow a short time before cancelling tasks
            await asyncio.sleep(close_timeout)
        # cancel any still-pending tasks
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    # run the monitoring coroutine
    loop.run_until_complete(_run_until())
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()

class Processor_local(Processor_base):
    successor = None  # terminal processor

    def __init__(self, nodes, location, bridges) -> None:
        super().__init__(location, (nodes, bridges))
         # used for logging identification
        self.location = location

        self.nodes = nodes
        self.bridges = bridges

        self.info(f'Creating Local Computer with {len(self.nodes)} nodes.')

    def __str__(self) -> str:
        return f"CMP-LC:{self.location}"
    
    # Base expects group_factory for loc==None
    @classmethod
    def group_factory(cls, items, bridges):
        # items: sub_tuples including node as last element
        nodes = [entry[-1] for entry in items]
        node_bridges = [bridges[str(n)] for n in nodes]
        return [cls(nodes, None, node_bridges)]

    # Abstract hooks for Processor_base
    def _make_events(self):
        self.ready_event = th.Event()
        self.start_event = th.Event()
        self.stop_event = th.Event()
        self.close_event = th.Event()

    def _make_queue(self):
       return None 
    
    def _make_worker(self, args, name):
        # spawn a local worker thread running the shared child entrypoint
        return th.Thread(target=local_child_main, args=args, name=name)

    def _kill_worker(self):
        # local worker should exit once event loop stops
        pass

    # Lifecycle for local computing is handled by shared `_child_main` function
    # No explicit `start` or `stop` needed here, base handles via events



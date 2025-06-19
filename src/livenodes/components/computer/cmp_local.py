import threading as th
from .cmp_common import Processor_base, EventHandshakeChild, EventHandshakeParent
import asyncio
from livenodes.components.node_logger import Logger
from logging.handlers import QueueHandler

def local_child_main(location, successor, successor_args,
                    ready_event, start_event, stop_event, close_event,
                    subprocess_log_queue):
    # the timeouts are only here for a  consistent interface,
    """Child entrypoint for local (asyncio) processors."""
    with EventHandshakeChild(*ready_event):
        log = Logger()
        logger = log.get_logger()
        if subprocess_log_queue:
            handler = QueueHandler(subprocess_log_queue)
            logger.addHandler(handler)
            # when using a queue handler, disable propagation to avoid duplicate logs
            logger.propagate = False
        else:
            # no queue for local processor: enable propagation so logs go to console
            logger.propagate = True
        log.info(f"[{location}] child_main starting >>>")

        
        nodes, bridges = successor_args

        # set up event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.set_exception_handler(lambda l, ctx: log.error(ctx) or l.default_exception_handler(ctx))

        # schedule ready tasks
        tasks = [asyncio.ensure_future(
                    node.ready(input_endpoints=b['recv'], output_endpoints=b['emit']),
                    loop=loop)
                for node, b in zip(nodes, bridges)]
        log.info('All Nodes ready')

    # wait until start
    with EventHandshakeChild(*start_event):
        log.info('Starting Nodes')
        for node in nodes:
            node.start()
        
    stop_request, stop_complete, stop_timeout = stop_event
    close_request, close_complete, close_timeout = close_event
    # wait until either all tasks complete or external stop_request
    async def _run_until():
        # gather all ready tasks
        all_done_future = asyncio.gather(*tasks)
        # run the monitoring coroutine
        stop_future = loop.run_in_executor(None, stop_request.wait)
        done, pending = await asyncio.wait(
            [all_done_future, stop_future], return_when=asyncio.FIRST_COMPLETED
        )
        # if stop_event triggered, handle external stop
        if stop_future in done:
            log.info('Stopping nodes')
            for node in nodes:
                try:
                    node.stop()
                except Exception:
                    log.exception(f"Error stopping node {node}")
            # give the nodes some time to stop gracefully
            # not sure if we even need a timeout here, as the nodes are not stopped asynchronously
            # await asyncio.sleep(stop_timeout)
            # let the loop run once to process stop events
            await asyncio.sleep(0)
            # wait for all nodes to finish -> then we might not cancel them if there is an issue with the stop call 
            # await asyncio.gather(*(node._finished for node in nodes), return_exceptions=True)
            # wait for close_event
            # signal to parent that local child has stopped
            stop_complete.set()
            await loop.run_in_executor(None, close_request.wait)
        else:
            # we will set the stop_request ourselves and then reset, as we cannot cancel the loop.run_in_executor(None, stop_request.wait) otherwise
            stop_request.set()
            stop_request.clear()
            # we did not need to stop, but we can still signal completion
            stop_complete.set()
        # cancel any still-pending tasks
        log.info('Canceling all remaining tasks')
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        
    loop.run_until_complete(_run_until())
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()
    close_complete.set()
    log.info(f"[{location}] child_main exiting <<<")


class Processor_local(Processor_base):
    successor = None  # terminal processor

    def __init__(self, nodes, location, bridges, **kwargs):
        super().__init__(location, (nodes, bridges), **kwargs)
         # used for logging identification
        self.location = location

        self.nodes = nodes
        self.bridges = bridges

        self.info(f'Creating {self.__class__.__name__} with {len(self.nodes)} nodes ({nodes[:10]}) at location {self.location}')


    def __str__(self) -> str:
        return f"CMP-LC:{self.location}"
    
    # Base expects group_factory for loc==None
    @classmethod
    def group_factory(cls, items, bridges, **kwargs):
        # the stop_timeout and close_timeout are only here for a consistent interface,
        # items: sub_tuples including node as last element
        nodes = [entry[-1] for entry in items]
        node_bridges = [bridges[str(n)] for n in nodes]
        return [cls(nodes, None, node_bridges, **kwargs)]
    
    # Abstract hooks for Processor_base
    def _make_events(self, ready_timeout=30, start_timeout=30, stop_timeout=30, close_timeout=30):
        self.evts_ready = (th.Event(), th.Event(), ready_timeout)
        self.evts_start = (th.Event(), th.Event(), start_timeout)
        self.evts_stop = (th.Event(), th.Event(), stop_timeout)
        self.evts_close = (th.Event(), th.Event(), close_timeout)

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



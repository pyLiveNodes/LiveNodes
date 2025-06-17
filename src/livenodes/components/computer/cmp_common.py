import logging
from logging.handlers import QueueHandler
import threading as th
from livenodes.components.node_logger import Logger
from itertools import groupby

def child_main(location, successor, successor_args,
                ready_event, start_event, stop_event, close_event,
                subprocess_log_queue, logger_name,
                stop_timeout, close_timeout):
    """Child process/thread entrypoint, runs the shared compute logic."""
    logger = logging.getLogger(logger_name)
    if subprocess_log_queue:
        handler = QueueHandler(subprocess_log_queue)
        logger.addHandler(handler)
        # when using a queue handler, disable propagation to avoid duplicate logs
        logger.propagate = False
    else:
        # no queue for local processor: enable propagation so logs go to console
        logger.propagate = True

    # enter
    logger.info(f"[{location}] child_main starting")
    computers = successor(*successor_args)
    logger.info(f"Created computers: {list(map(str, computers))}")
    # setup subcomputers
    for c in computers:
        c.setup()
    ready_event.set()
    
    # wait for start signal
    start_event.wait()
    for proc in computers:
        proc.start()
    
    # wait on stop_event or all finish
    all_done = False
    while not stop_event.wait(timeout=0.1) and not all_done:
        all_done = all(c.is_finished() for c in computers)
    
    if not all_done:
        for proc in computers:
            proc.stop(timeout=stop_timeout)
        close_event.wait()
        for proc in computers:
            proc.close(timeout=close_timeout)
    
    # exit
    logger.info(f"[{location}] child_main exiting")

class Processor_base(Logger):
    """
    Base class for processor implementations, handling common setup, threading/process control, and logging.
    """
    successor = None
    # default child entrypoin

    @classmethod
    def group_factory(cls, items, bridges):
        """
        items: List of tuples where the first element is the thread/process key
                       and the remaining elements are passed downstream. The last item should be the node itself
        bridges:       Mapping from node‐id to bridge endpoint.
        logger_fn:     Callable for logging.
        """
        computers = []
        # sort & group by the first tuple‐element (process key)
        items = sorted(items, key=lambda t: t[0])
        for loc, group in groupby(items, key=lambda t: t[0]):
            entries = list(group)
            # drop the used loc key, keep the remaining sub‐tuples / locations
            sub_tuples = [entry[1:] for entry in entries]
            # select only those bridges that are used by the sub‐tuples / entries of this group
            sub_bridges = {str(entry[-1]): bridges[str(entry[-1])] for entry in entries}

            if not loc:
                # no loc specified: hand off directly to successor so that it can be owned by our caller instead of us, since we are not used
                computers.extend(cls.successor(sub_tuples, sub_bridges))
            else:
                # loc specified: build a Processor_process that owns its sub‐tuples
                computers.append(cls(location=loc, successor_args=(sub_tuples, sub_bridges)))

        return computers


    def __init__(self, location, successor_args, stop_timeout=30, close_timeout=30):
        super().__init__()
        self.location = location
        self.successor_args = successor_args
        self.stop_timeout = stop_timeout
        self.close_timeout = close_timeout
        self.create_locks_for_next_run()
        self.info(f'Creating {self.__class__.__name__} with {len(self.successor_args[0])} nodes.')

    def create_locks_for_next_run(self):
        """
        Initialize locks by delegating to subclass event creation and resetting worker.
        """
        # subclass-specific event setup
        self._make_events()
        # common controls
        self.worker_log_handler_termi_sig = th.Event()
        self.worker = None
        # ensure signals cleared
        self.start_event.clear()
        self.stop_event.clear()
        self.close_event.clear()

        self.queue_listener = None


    def _make_events(self):
        """
        Abstract: subclasses should initialize self.ready_event, start_event, stop_event, close_event.
        """
        raise NotImplementedError

    def __str__(self):
        return f"CMP-PR:{self.location}"

    def setup(self):
        """Common setup: logging queue, drainer thread, and worker start."""
        self.info('Readying')

        self.parent_log_queue = self._make_queue()
        logger_name = 'livenodes'
        # use QueueListener instead of manual drain thread
        if self.parent_log_queue is not None:
            from logging.handlers import QueueHandler, QueueListener
            logger = logging.getLogger(logger_name)
            # capture existing handlers and remove them from logger
            existing_handlers = logger.handlers[:]
            for h in existing_handlers:
                logger.removeHandler(h)
            # start listener to handle queued records
            self.queue_listener = QueueListener(self.parent_log_queue, *existing_handlers)
            self.queue_listener.start()
            # attach queue handler to logger
            logger.addHandler(QueueHandler(self.parent_log_queue))
            logger.propagate = False

        self.info('Creating worker')
        # start child via subclass-defined entrypoint
        self.worker = self._make_worker(
            args=(self.location, self.successor, self.successor_args,
                  self.ready_event, self.start_event,
                  self.stop_event, self.close_event,
                  self.parent_log_queue, logger_name,
                  self.stop_timeout, self.close_timeout),
            name=str(self)
        )
        self.info('Starting worker')
        self.worker.start()
        self.info(f"  → workername: {self.worker.name}")

        self.info('Waiting for worker to be ready')
        if not self.ready_event.wait(timeout=100):
            self.error('Worker did not become ready in time, terminating')
            self._kill_worker()
            raise RuntimeError('Worker did not become ready in time')
        self.info('Worker ready, resuming')

    def start(self):
        """Signal worker to start processing."""
        self.info('Starting')
        self.start_event.set()

    def join(self, timeout=None):
        """Wait for worker to finish if processing ends."""
        self.info('Joining')
        if self.worker:
            self.worker.join(timeout)

    def stop(self, timeout=100):
        """Signal worker to stop and wait for thread/process to exit."""
        self.info('Stopping')
        self.stop_event.set()
        if self.worker:
            self.worker.join(timeout)
        alive = self.worker.is_alive() if self.worker else False
        self.info(f"Returning; Worker finished: {not alive}")

    def close(self, timeout=100):
        """Signal close, wait, and clean up logging and worker."""
        self.info('Closing')
        self.close_event.set()
        if self.worker:
            self.worker.join(timeout / 2)
            if self.worker.is_alive():
                self.info('Timeout reached: worker still alive')

        # stop and cleanup queue listener if used
        if self.queue_listener:
            self.info('Closing Log QueueListener')
            self.queue_listener.stop()
            self.queue_listener = None

        # clean up parent log resources
        self.parent_log_queue = None

        self.info('Resetting for next run')
        self.create_locks_for_next_run()

    def is_finished(self):
        """Return True if worker thread/process has exited."""
        return self.worker is not None and not self.worker.is_alive()

    def check_threads_finished(self, computers):
        return all(c.is_finished() for c in computers)

    # Abstract methods to implement in subclasses
    def _make_queue(self):
        raise NotImplementedError

    def _make_worker(self, args, name):
        # e.g. return th.Thread(target=child_main, args=args, name=name)
        raise NotImplementedError

    def _kill_worker(self):
        raise NotImplementedError

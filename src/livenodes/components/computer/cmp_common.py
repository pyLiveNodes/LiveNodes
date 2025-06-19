import logging
from logging.handlers import QueueHandler
from livenodes.components.node_logger import Logger
from itertools import groupby

class EventHandshakeParent:
    def __init__(self, req_evt, done_evt, timeout=None):
        self.request, self.complete, self.timeout = req_evt, done_evt, timeout

    def __enter__(self):
        self.request.set()
        # swallow nothing–propagate exceptions normally
        return self

    def __exit__(self, exc_type, exc, tb):
        if not self.complete.wait(self.timeout):
            raise TimeoutError("stop request never arrived")
        

class EventHandshakeChild:
    def __init__(self, req_evt, done_evt, timeout=None):
        self.request, self.complete, self.timeout = req_evt, done_evt, timeout

    def __enter__(self):
        if not self.request.wait(self.timeout):
            raise TimeoutError("stop request never arrived")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.complete.set()
        # swallow nothing–propagate exceptions normally

def child_main(location, successor, successor_args,
                ready_event, start_event, stop_event, close_event,
                subprocess_log_queue):
    """Child process/thread entrypoint, runs the shared compute logic."""
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

        # enter
        log.info(f"[{location}] child_main starting >>>")
        computers = successor(*successor_args, start_timeout=start_event[-1],
                            stop_timeout=stop_event[-1], close_timeout=close_event[-1])
        log.info(f"Created computers: {list(map(str, computers))}")
        # setup subcomputers
        for c in computers:
            c.setup()
    
    # wait for start signal
    with EventHandshakeChild(*start_event):
        log.info('Starting Computers')
        for proc in computers:
            proc.start()
    
    # wait on stop_request or all finish
    stop_request, stop_complete, stop_timeout = stop_event
    all_done = False
    while not stop_request.wait(timeout=0.1) and not all_done:
        all_done = all(c.is_finished() for c in computers)

    log.info(f'Requested stop: {stop_request.is_set()}, All Done: {all_done}')
    if not all_done:
        log.info('Stopping all computers')
        for proc in computers:
            proc.stop()
        stop_complete.set()
        
        with EventHandshakeChild(*close_event):
            for proc in computers:
                proc.close()
    
    # exit
    log.info(f"[{location}] child_main exiting <<<")

class Processor_base(Logger):
    """
    Base class for processor implementations, handling common setup, threading/process control, and logging.
    """
    successor = None
    # default child entrypoint

    @classmethod
    def group_factory(cls, items, bridges, start_timeout=30, stop_timeout=30, close_timeout=30):
        """
        items: List of tuples where the first element is the thread/process key
                       and the remaining elements are passed downstream. The last item should be the node itself
        bridges:       Mapping from node‐id to bridge endpoint.
        logger_fn:     Callable for logging.
        """
        computers = []
        # sort & group by the first tuple‐element (process key)
        items = list(sorted(items, key=lambda t: t[0]))
        l = len(items) if len(items) > 0 else 1

        for loc, group in groupby(items, key=lambda t: t[0]):
            entries = list(group)
            # drop the used loc key, keep the remaining sub‐tuples / locations
            sub_tuples = [entry[1:] for entry in entries]
            # select only those bridges that are used by the sub‐tuples / entries of this group
            # select based on the last element of the entry, which is the node itself and str(node) is the unique identifier
            sub_bridges = {str(entry[-1]): bridges[str(entry[-1])] for entry in entries}

            if not loc:
                # no loc specified: hand off directly to successor so that it can be owned by our caller instead of us, since we are not used
                computers.extend(cls.successor(sub_tuples, sub_bridges, start_timeout=start_timeout, stop_timeout=stop_timeout, close_timeout=close_timeout))
            else:
                # loc specified: build a Processor_process that owns its sub‐tuples
                computers.append(cls(location=loc, successor_args=(sub_tuples, sub_bridges), start_timeout=start_timeout / l, stop_timeout=stop_timeout / l, close_timeout=close_timeout / l))

        return computers


    def __init__(self, location, successor_args, start_timeout=30, stop_timeout=30, close_timeout=30):
        super().__init__()
        self.location = location
        self.successor_args = successor_args
        self.start_timeout = start_timeout
        self.stop_timeout = stop_timeout
        self.close_timeout = close_timeout
        self.create_locks_for_next_run()
        self.info(f'Creating {self.__class__.__name__} with {len(self.successor_args[0])} nodes ({self.successor_args[0][:10]}) at location {self.location}')

    def create_locks_for_next_run(self):
        """
        Initialize locks by delegating to subclass event creation and resetting worker.
        """
        # subclass-specific event setup
        self._make_events()
        # reset worker and queue listener
        self.worker = None
        self.queue_listener = None
        self.parent_log_queue = None

    def setup(self):
        """Common setup: logging queue, drainer thread, and worker start."""
        self.info('Readying')

        self.parent_log_queue = self._make_queue()
        # use QueueListener instead of manual drain thread
        if self.parent_log_queue is not None:
            from logging.handlers import QueueHandler, QueueListener
            logger = logging.getLogger(self.logger_name)
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
        # pass stop_request and stop_complete instead of single stop_event
        self.worker = self._make_worker(
            args=(self.location, self.successor, self.successor_args,
                  self.evts_ready, self.evts_start,
                  self.evts_stop, self.evts_close,
                  self.parent_log_queue),
            name=str(self)
        )
        self.info('Starting worker')
        self.worker.start()
        self.info(f"  → workername: {self.worker.name}")

        self.info('Waiting for worker to be ready')
        try:
            with EventHandshakeParent(*self.evts_ready):
                self.info('Worker ready handshake complete')
        except TimeoutError:
            self.error('Worker did not become ready in time, terminating')
            self._kill_worker()
            raise RuntimeError('Worker did not become ready in time')


    def start(self):
        """Signal worker to start processing."""
        self.info('Starting')
        self.evts_start[0].set()

    def join(self, timeout=None):
        """Wait for worker to finish if processing ends."""
        self.info('Joining')
        if self.worker:
            self.worker.join(timeout)

    def stop(self):
        """Signal worker to stop and wait for thread/process to exit via handshake."""
        self.info(f'Requesting worker stop with timeout {self.evts_stop[-1]}')
        try:
            with EventHandshakeParent(*self.evts_stop):
                self.info('Worker stop handshake complete')
        except TimeoutError:
            self.warn('Worker did not acknowledge stop request in time -> close() will kill it')
        
    def close(self):
        """Signal close, wait, and clean up logging and worker."""
        self.info(f'Closing worker {self.worker.name if self.worker else "None"} with timeout {self.stop_timeout}')
        # signal the child to exit
        try:
            with EventHandshakeParent(*self.evts_close):
                self.info('Worker close handshake complete')
        except TimeoutError:
            self.warn('Worker did not acknowledge close request in time -> force termination')
            # if the worker did not exit cleanly, we will try to kill it
            self._kill_worker()
        
        # stop and cleanup queue listener if used
        if self.queue_listener:
            self.info('Closing Log QueueListener')
            self.queue_listener.stop()
            self.queue_listener = None

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

    def _make_events(self):
        """
        Abstract: subclasses should initialize self.evts_ready, start_event, stop_event, close_event.
        """
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError(
            f"Processor_base subclass {self.__class__.__name__} must implement __str__()"
        )

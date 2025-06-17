import logging
from logging.handlers import QueueHandler
import threading as th
from livenodes.components.node_logger import Logger
from livenodes.components.utils.log import drain_log_queue
from itertools import groupby

class Processor_base(Logger):
    """
    Base class for processor implementations, handling common setup, threading/process control, and logging.
    """
    successor = None

    @classmethod
    def group_factory(cls, items, bridges, logger_fn):
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
            # drop the loc key, keep the remaining sub‐tuples
            sub_tuples = [entry[1:] for entry in entries]
            logger_fn(f"Resolving computer group. Location: {loc}; Items: {len(sub_tuples)}")

            if not loc:
                # no loc specified: hand off directly to threads
                computers.extend(cls.successor(sub_tuples, bridges, logger_fn))
            else:
                # loc specified: build a Processor_process that owns its sub‐tuples
                nodes = [st[-1] for st in sub_tuples]
                node_bridges = [bridges[str(n)] for n in nodes]
                successor_args = (sub_tuples, node_bridges, logger_fn)
                computers.append(cls(location=loc, successor_args=successor_args))

        return computers


    def __init__(self, location, successor_args, stop_timeout=0.1, close_timeout=0.1):
        super().__init__()
        self.location = location
        self.successor_args = successor_args
        self.stop_timeout_threads = stop_timeout
        self.close_timeout_threads = close_timeout
        self.worker = None
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

        # start log draining thread
        self.worker_log_handler = th.Thread(
            target=drain_log_queue,
            args=(self.parent_log_queue, logger_name, self.worker_log_handler_termi_sig)
        )
        self.worker_log_handler.daemon = True
        self.worker_log_handler.name = f"LogDrain-{self.worker_log_handler.name.split('-')[-1]}"
        self.worker_log_handler.start()

        # start worker thread/process
        self.worker = self._make_worker(
            target=self.start_subprocess,
            args=(self.successor_args, self.parent_log_queue, logger_name,),
            name=str(self)
        )
        self.worker.start()

        self.info('Waiting for worker to be ready')
        if not self.ready_event.wait(timeout=10):
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

    def stop(self, timeout=0.3):
        """Signal worker to stop and wait for thread/process to exit."""
        self.info('Stopping')
        self.stop_event.set()
        if self.worker:
            self.worker.join(timeout)
        alive = self.worker.is_alive() if self.worker else False
        self.info(f"Returning; Worker finished: {not alive}")

    def close(self, timeout=0.5):
        """Signal close, wait, and clean up logging and worker."""
        self.info('Closing')
        self.close_event.set()
        if self.worker:
            self.worker.join(timeout / 2)
            if self.worker.is_alive():
                self.info('Timeout reached: worker still alive')

        self.info('Closing Log Drain')
        self.worker_log_handler_termi_sig.set()
        self.worker_log_handler.join(timeout / 2)

        # clean up parent log resources
        self.parent_log_queue = None
        self.worker_log_handler = None

        self.info('Resetting for next run')
        self.create_locks_for_next_run()

    def is_finished(self):
        """Return True if worker thread/process has exited."""
        return self.worker is not None and not self.worker.is_alive()

    def check_threads_finished(self, computers):
        return all(c.is_finished() for c in computers)

    def start_subprocess(self, successor_args, subprocess_log_queue, logger_name):
        """Shared subprocess logic for both threading and multiprocessing implementations."""
        logger = logging.getLogger(logger_name)
        logger.addHandler(QueueHandler(subprocess_log_queue))
        logger.propagate = False

        self.info('Starting Process')

        computers = self.successor(*successor_args, logger_fn=self.info)
        self.info(f"Created computers: {list(map(str, computers))}")

        try:
            self.info('Setting up computers')
            for c in computers:
                c.setup()
        except Exception:
            self.error('Sub-computer setup failed', exc_info=True)
            self.ready_event.set()
            raise

        self.info('All Computers ready')
        self.ready_event.set()

        # wait for start signal
        self.start_event.wait()
        self.info('Starting Computers')
        for proc in computers:
            proc.start()

        all_done = False
        while not self.stop_event.wait(timeout=0.1) and not all_done:
            all_done = all(c.is_finished() for c in computers)

        if all_done:
            self.info('All Computers have finished, returning')
        else:
            self.info('Stopping Computers')
            for proc in computers:
                proc.stop(timeout=self.stop_timeout_threads)

            self.close_event.wait()
            self.info('Closing Computers')
            for proc in computers:
                proc.close(timeout=self.close_timeout_threads)

        self.info('Finished Process and returning')

    # Abstract methods to implement in subclasses
    def _make_queue(self):
        raise NotImplementedError

    def _make_worker(self, target, args, name):
        raise NotImplementedError

    def _kill_worker(self):
        raise NotImplementedError

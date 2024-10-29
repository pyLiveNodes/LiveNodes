
import logging
from logging.handlers import QueueHandler
import threading as th
import multiprocessing as mp
from itertools import groupby
from livenodes.components.utils.log import drain_log_queue
from livenodes.components.node_logger import Logger

from .cmp_thread import Processor_threads

# import platform
# if platform.system() == 'Darwin':
#         mp.set_start_method(
#             'fork',
#             force=True)
mp.set_start_method('spawn', force=True)


class Processor_process(Logger):
    def __init__(self, nodes, location, bridges, stop_timeout_threads=0.1, close_timeout_threads=0.1) -> None:
        super().__init__()
        # -- both processes
        # indicates that the subprocess is ready
        self.ready_event = mp.Event() 
        # indicates that the readied nodes should start sending data
        self.start_lock = mp.Lock() 
        # indicates that the started nodes should stop sending data
        self.stop_lock = mp.Lock() 
        # indicates that the thread should be closed without waiting on the nodes to finish
        self.close_lock = mp.Lock() 
        # used for logging identification
        self.location = location
        # tell log drainer thread that it should return 
        self.worker_log_handler_termi_sig = th.Event()

        # -- main process
        self.nodes = nodes
        self.bridges = bridges
        self.subprocess = None
        self.start_lock.acquire()
        self.stop_lock.acquire()
        self.close_lock.acquire()

        self.info(f'Creating Process Computer with {len(self.nodes)} nodes.')


    def __str__(self) -> str:
        return f"CMP-PR:{self.location}"

    # parent process
    def setup(self):
        self.info('Readying')

        parent_log_queue = mp.Queue()
        logger_name = 'livenodes'
        
        self.worker_log_handler = th.Thread(target=drain_log_queue, args=(parent_log_queue, logger_name, self.worker_log_handler_termi_sig))
        self.worker_log_handler.deamon = True
        self.worker_log_handler.name = f"LogDrain-{self.worker_log_handler.name.split('-')[-1]}"
        self.worker_log_handler.start()

        self.subprocess = mp.Process(
            target=start_subprocess,
            args=(self.nodes, self.bridges, 
                self.ready_event, self.start_lock, self.stop_lock, self.close_lock,
                parent_log_queue, logger_name,
                self.stop_timeout_threads, self.close_timeout_threads), name=str(self))
        self.subprocess.start()
        
        self.info('Waiting for worker to be ready')
        self.ready_event.wait(timeout=0.1)
        self.info('Worker ready, resuming')

    # parent process
    def start(self):
        self.info('Starting')
        self.start_lock.release()

    # TODO: this will not work
    # as: the start() of the thread processor used inside of this processors supbrocess are non-blockign
    # therefore: we are waiting on the stop-lock which will be released once someone calls stop -> thus joining the subprocess will never return!
    # in the join case we would want to be able to join each thread cmp instead of waiting on stop or close...
    # FIXED: inside of the subprocess we are short_ciruiting the stop and close locks if the threads have returned by themselves, thus the join returns once close is called or the sub-threads return
    # parent process
    def join(self, timeout=None):
        """ used if the processing is nown to end"""
        self.info('Joining')
        self.subprocess.join(timeout)

    # parent process
    def stop(self, timeout=0.1):
        """ used if the processing is nown to be endless"""

        self.info('Stopping')
        self.stop_lock.release()
        self.subprocess.join(timeout)
        self.info('Returning; Process finished: ', not self.subprocess.is_alive())

    # parent process
    def close(self, timeout=0.1):
        self.info('Closing')
        self.close_lock.release()
        self.subprocess.join(timeout)
        if self.subprocess.is_alive():
            self.subprocess.terminate()
            self.info('Timout reached: killed process')
        # self.subprocess = None
        self.info('Closing Log Drain')
        self.worker_log_handler_termi_sig.set()

    # parent thread
    def is_finished(self):
        return self.subprocess is not None and not self.subprocess.is_alive()
        

    # worker process
    @staticmethod
    def check_threads_finished(computers):
        return all([cmp.is_finished() for cmp in computers])

def start_subprocess(nodes, bridges, ready_event, start_lock, stop_lock, close_lock, subprocess_log_queue, logger_name, stop_timeout_threads, close_timeout_threads):
    worker = Worker_Process(
        nodes=nodes,
        bridges=bridges,
        ready_event=ready_event,
        start_lock=start_lock,
        stop_lock=stop_lock,
        close_lock=close_lock,
        subprocess_log_queue=subprocess_log_queue,
        logger_name=logger_name,
        stop_timeout_threads=stop_timeout_threads,
        close_timeout_threads=close_timeout_threads
    )
    worker.start()

class Worker_Process(Logger):
    def __init__(self, nodes, bridges, ready_event, start_lock, stop_lock, close_lock, subprocess_log_queue, logger_name, stop_timeout_threads, close_timeout_threads):
        super().__init__()
        self.nodes = nodes
        self.bridges = bridges
        self.ready_event = ready_event
        self.start_lock = start_lock
        self.stop_lock = stop_lock
        self.close_lock = close_lock
        self.subprocess_log_queue = subprocess_log_queue
        self.logger_name = logger_name
        self.stop_timeout_threads = stop_timeout_threads
        self.close_timeout_threads = close_timeout_threads
        self.computers = []

    def start(self):
        logger = logging.getLogger(self.logger_name)
        logger.addHandler(QueueHandler(self.subprocess_log_queue))

        logger.info('Starting Process')

        bridge_lookup = {str(node): bridge for node, bridge in zip(self.nodes, self.bridges)}
        locations = groupby(sorted(self.nodes, key=lambda n: n.compute_on), key=lambda n: n.compute_on)
        
        for loc, loc_nodes in locations:
            loc_nodes = list(loc_nodes)
            logger.info(f'Resolving computer group. Location: {loc}; Nodes: {len(loc_nodes)}')
            node_specific_bridges = [bridge_lookup[str(n)] for n in loc_nodes]
            cmp = Processor_threads(nodes=loc_nodes, location=loc, bridges=node_specific_bridges)
            self.computers.append(cmp)
        
        logger.info('Created computers:', list(map(str, self.computers)))
        logger.info('Setting up computers')
        
        for cmp in self.computers:
            cmp.setup()

        logger.info('All Computers ready')
        self.ready_event.set()

        self.start_lock.acquire()
        logger.info('Starting Computers')
        
        for cmp in self.computers:
            cmp.start()

        self.monitor_computers(logger)

    def monitor_computers(self, logger):
        all_computers_finished = False
        
        while not self.stop_lock.acquire(timeout=0.1) and not all_computers_finished:
            all_computers_finished = all([cmp.is_finished() for cmp in self.computers])
        
        if all_computers_finished:
            logger.info('All Computers have finished, returning')
        else:
            logger.info('Stopping Computers')
            for cmp in self.computers:
                cmp.stop(timeout=self.stop_timeout_threads)

            # if not all_computers_finished:
            self.close_lock.acquire()
            logger.info('Closing Computers')
            for cmp in self.computers:
                cmp.close(timeout=self.close_timeout_threads)

        logger.info('Finished Process and returning')

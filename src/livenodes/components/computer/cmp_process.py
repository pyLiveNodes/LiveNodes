import multiprocessing as mp
from .cmp_common import Processor_base, child_main
from .cmp_thread import Processor_threads

# use spawn context for multiprocessing to ensure Events and Manager work under macOS spawn
MP_CTX = mp.get_context('fork')

class Processor_process(Processor_base):
    successor = Processor_threads.group_factory

    def __str__(self):
        return f"CMP-PR:{self.location}"

    def _make_events(self, ready_timeout=30, start_timeout=30, stop_timeout=30, close_timeout=30):
        # Manager-based events for inter-process
        self.manager = MP_CTX.Manager()
        self.evts_ready = (self.manager.Event(), self.manager.Event(), ready_timeout)
        self.evts_start = (self.manager.Event(), self.manager.Event(), start_timeout)
        self.evts_stop = (self.manager.Event(), self.manager.Event(), stop_timeout)
        self.evts_close = (self.manager.Event(), self.manager.Event(), close_timeout)

    def _make_queue(self):
        # use spawn-context Queue to avoid forking issues
        return MP_CTX.Queue()

    def _make_worker(self, args, name):
        # spawn a child process using the shared child_main entrypoint
        return MP_CTX.Process(target=child_main, args=args, name=name)

    def _kill_worker(self):
        if self.worker and self.worker.is_alive():
            self.worker.terminate()
            self.worker.join()
        self.worker = None

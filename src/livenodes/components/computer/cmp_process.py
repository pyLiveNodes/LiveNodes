import multiprocessing as mp
from .cmp_common import Processor_base
from .cmp_thread import Processor_threads

# use spawn context for multiprocessing to ensure Events and Manager work under macOS spawn
MP_CTX = mp.get_context('spawn')

class Processor_process(Processor_base):
    successor = Processor_threads.group_factory

    def _make_events(self):
        # Manager-based events for inter-process
        self.manager = MP_CTX.Manager()
        self.ready_event = self.manager.Event()
        self.start_event = self.manager.Event()
        self.stop_event = self.manager.Event()
        self.close_event = self.manager.Event()

    def _make_queue(self):
        return mp.Queue()

    def _make_worker(self, target, args, name):
        return mp.Process(target=target, args=args, name=name)

    def _kill_worker(self):
        if self.worker and self.worker.is_alive():
            self.worker.terminate()
            self.worker.join()
        self.worker = None

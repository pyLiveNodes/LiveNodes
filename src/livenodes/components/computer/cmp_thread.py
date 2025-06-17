import threading as th
from .cmp_common import Processor_base, child_main
from .cmp_local import Processor_local

class Processor_threads(Processor_base):
    successor = Processor_local.group_factory

    # abstract methods to implement
    def _make_events(self):
        self.ready_event = th.Event()
        self.start_event = th.Event()
        self.stop_event = th.Event()
        self.close_event = th.Event()

    def _make_queue(self):
        return None

    def _make_worker(self, args, name):
        return th.Thread(target=child_main, args=args, name=name)

    def _kill_worker(self):
        if self.worker and self.worker.is_alive():
            self.info('Cannot terminate thread; ignoring')
        self.worker = None

    def __str__(self) -> str:
        return f"CMP-PR:{self.location}"

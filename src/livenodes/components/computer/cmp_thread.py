import threading as th
from .cmp_common import Processor_base, child_main
from .cmp_local import Processor_local

class Processor_threads(Processor_base):
    successor = Processor_local.group_factory

    def __str__(self):
        return f"CMP-TH:{self.location}"

    # abstract methods to implement
    def _make_events(self, ready_timeout=30, start_timeout=30, stop_timeout=30, close_timeout=30):
        self.evts_ready = (th.Event(), th.Event(), ready_timeout)
        self.evts_start = (th.Event(), th.Event(), start_timeout)
        self.evts_stop = (th.Event(), th.Event(), stop_timeout)
        self.evts_close = (th.Event(), th.Event(), close_timeout)

    def _make_queue(self):
        return None

    def _make_worker(self, args, name):
        return th.Thread(target=child_main, args=args, name=name)

    def _kill_worker(self):
        if self.worker and self.worker.is_alive():
            self.info('Cannot terminate thread; ignoring')
        self.worker = None

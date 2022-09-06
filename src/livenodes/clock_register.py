import multiprocessing as mp
import threading

# TODO: this is bs, remove pls!
# more precise: the node system was never designed for a single instance runner, and thus will have unintended side effects...
class Clock_Register():
    state = {}

    queue = mp.SimpleQueue()

    _store = mp.Event()

    def __init__(self):
        self._owner_process = mp.current_process()
        self._owner_thread = threading.current_thread()

    # called in sub-processes
    def register(self, node_id, ctr):
        if not self._store.is_set():
            self.queue.put(node_id, ctr)

    def set_passthrough(self, node):
        print(f"Clock_Register set to passthrough by {str(node)}")
        self._store.set()
        self.queue = None

    # called in main/handling process
    def read_state(self):
        if self._owner_process != mp.current_process():
            raise Exception('Called from wrong process')
        if self._owner_thread != threading.current_thread():
            raise Exception('Called from wrong thread')
        if self._store.is_set():
            raise Exception('Clock Register was set to passthrough')

        while not self.queue.empty():
            name, ctr = self.queue.get()
            if name not in self.state:
                self.state[name] = []

            self.state[name].append(ctr)

        return self.state

    def all_at(self, ctr):
        states = self.read_state()

        for ctrs in states.values():
            if max(ctrs) < ctr:
                return False

<<<<<<< HEAD
        return True
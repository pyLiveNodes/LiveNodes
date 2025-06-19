import time
import pickle
from multiprocessing import shared_memory, Lock

from .node import Node
from .components.utils.reportable import Reportable

import os
SHM_SIZE = int(os.getenv('SHM_SIZE', 1_048_576))  # Default to 1MB if not set

class View(Node, abstract_class=True):
    _shm_size = SHM_SIZE

    def register_reporter(self, reporter_fn):
        if hasattr(self, 'fps'):
            self.fps.register_reporter(reporter_fn)
        return super().register_reporter(reporter_fn)
    
    def get_current_state(self):
        """
        Returns the current state of the view, which is the latest data emitted to the draw process
        """
        with self._shm_lock:
            # if already-read flag is set, no new data
            # read payload length from bytes 1..9
            length = int.from_bytes(self._shm.buf[1:9], 'little')
            if self._shm.buf[0] == 0 and length > 0:
                raw = bytes(self._shm.buf[9:9 + length])
                current_state = pickle.loads(raw)
                self._shm.buf[0] = 1
                return current_state
        return {}

    def init_draw(self, *args, **kwargs):
        """
        Heart of the nodes drawing, should be a functional function
        """

        update_fn = self._init_draw(*args, **kwargs)

        def update():
            cur_state = self.get_current_state()
            # decide if we should draw
            if self._should_draw(**cur_state):
                self.debug('[Draw]', cur_state.keys())
                res = update_fn(**cur_state)
                self.fps.count()
                return res
            else:
                self.debug('[Skipped Draw]', cur_state.keys())
                return None

        return update
    
    def _onstart(self, **kwargs):
        """
        Called when the view is started, initializes the shared memory and draw state
        """
        # initialize shared memory for draw state
        if not hasattr(self, '_shm') or self._shm is None:
            self._shm = shared_memory.SharedMemory(create=True, size=self._shm_size)
            self._shm_lock = Lock()
            # reserve first 8 bytes for payload length (little-endian)
            self._shm.buf[0] = 1
            self._shm.buf[1:9] = (0).to_bytes(8, 'little')

        super()._onstart(**kwargs)

    def _onstop(self, **kwargs):
        # clean up shared memory used for draw state
        if hasattr(self, '_shm') and self._shm is not None:
            self._shm.close()
            self._shm.unlink()
            self._shm = None

        # sets _running to false
        super()._onstop(**kwargs)

    def _init_draw(self):
        """
        Similar to init_draw, but specific to matplotlib animations
        Should be either or, not sure how to check that...
        """

        def update():
            pass

        return update

    def _should_draw(self, **cur_state):
        return bool(cur_state)

    def _emit_draw(self, **kwargs):
        """
        Called in computation process, ie self.process
        Emits data to draw process, ie draw_inits update fn
        """
        self.debug('Storing for draw:', kwargs.keys())
        # pickle and write into shared memory
        payload = pickle.dumps(kwargs)
        length = len(payload)
        # account for 1 flag byte + 8 length bytes
        if length + 9 > self._shm_size:
            raise RuntimeError(f"Draw state payload too large ({length} bytes)")
        with self._shm_lock:
            # clear read-flag, then write new length+payload
            self._shm.buf[0] = 0
            self._shm.buf[1:9] = length.to_bytes(8, 'little')
            self._shm.buf[9:9 + length] = payload

class FPS_Helper(Reportable):
    def __init__(self, name, report_every_x_seconds=5, **kwargs):
        super().__init__(**kwargs)

        self.name = name
        self.n_frames = 0
        self.n_frames_total = 0
        self.report_every_x_seconds = report_every_x_seconds
        self.timer = time.time()

    def count(self):
        self.n_frames += 1
        el_time = time.time() - self.timer
        if el_time > self.report_every_x_seconds:
            self.n_frames_total += self.n_frames
            self._report(fps={'fps': self.n_frames / el_time, 'total_frames': self.n_frames_total, 'name': self.name})
            self.timer = time.time()
            self.n_frames = 0

def print_fps(fps, **kwargs):
    print(f"Current fps: {fps['fps']:.2f} (Total frames: {fps['total_frames']}) -- {fps['name']}")


class View_MPL(View, abstract_class=True):
    def _init_draw(self, subfig):
        """
        Similar to init_draw, but specific to matplotlib animations
        Should be either or, not sure how to check that...
        """

        def update(**kwargs):
            raise NotImplementedError()

        return update

    def init_draw(self, subfig):
        """
        Heart of the nodes drawing, should be a functional function
        """

        update_fn = self._init_draw(subfig)
        # used in order to return the last artists, if the node didn't want to draw
        # ie create a variable outside of the update scope, that we can assign lists to
        artis_storage = {'returns': []}

        if self.should_time:
            self.fps = FPS_Helper(str(self), report_every_x_seconds=0.5)
        else:
            self.fps = FPS_Helper(str(self))
            self.fps.register_reporter(print_fps)

        def update(*args, **kwargs):
            nonlocal update_fn, artis_storage, self
            cur_state = {}

            cur_state = self.get_current_state()
            # always execute the update, even if no new data is added, as a view might want to update not based on the self emited data
            # this happens for instance if the view wants to update based on user interaction (and not data)
            if self._should_draw(**cur_state):
                self.debug('[Draw]', cur_state.keys())
                artis_storage['returns'] = update_fn(**cur_state)
                self.fps.count()
            else:
                self.debug('[Skipped Draw]', cur_state.keys())

            return artis_storage['returns']

        return update


class View_QT(View, abstract_class=True):
    def _init_draw(self, parent):
        pass

    def init_draw(self, parent):
        """
        Heart of the nodes drawing, should be a functional function
        """
        update_fn = self._init_draw(parent=parent)

        # if there is no update function only _init_draw will be needed / called
        if update_fn is not None:
            if self.should_time:
                self.fps = FPS_Helper(str(self), report_every_x_seconds=0.5)
            else:
                self.fps = FPS_Helper(str(self))
                self.fps.register_reporter(print_fps)

            # TODO: figure out more elegant way to not have this blocking until new data is available...
            def update_blocking():
                nonlocal update_fn, self
                cur_state = self.get_current_state()
                # always execute the update, even if no new data is added, as a view might want to update not based on the self emited data
                # this happens for instance if the view wants to update based on user interaction (and not data)
                if self._should_draw(**cur_state):
                    self.debug('[Draw]', cur_state.keys())
                    update_fn(**cur_state)
                    self.fps.count()
                    return True
                else:
                    self.debug('[Skipped Draw]', cur_state.keys())
                return False

            return update_blocking
        self.debug('No update function was returned, as none exists.')
        return None

class View_Vispy(View, abstract_class=True):
    def _init_draw(self, fig):
        def update(**kwargs):
            raise NotImplementedError()
        return update

    def init_draw(self, fig):
        """
        Heart of the nodes drawing, should be a functional function
        """
        update_fn = self._init_draw(fig)

        if self.should_time:
            self.fps = FPS_Helper(str(self), report_every_x_seconds=0.5)
        else:
            self.fps = FPS_Helper(str(self))
            self.fps.register_reporter(print_fps)

        # TODO: figure out more elegant way to not have this blocking until new data is available...
        def update_blocking():
            nonlocal update_fn, self
            cur_state = self.get_current_state()
            # always execute the update, even if no new data is added, as a view might want to update not based on the self emited data
            # this happens for instance if the view wants to update based on user interaction (and not data)
            if self._should_draw(**cur_state):
                self.debug('[Draw]', cur_state.keys())
                update_fn(**cur_state)
                self.fps.count()
                return True
            else:
                self.debug('[Skipped Draw]', cur_state.keys())
            return False

        return update_blocking

import multiprocessing as mp
import queue
import time
from PyQt5.QtWidgets import QLabel, QVBoxLayout

from .node import Node, Location
from .utils import noop



class View(Node):
    def __init__(self, name, compute_on=Location.SAME):
        super().__init__(name, compute_on)

        # TODO: consider if/how to disable the visualization of a node?
        # self.display = display

        # TODO: evaluate if one or two is better as maxsize (the difference should be barely noticable, but not entirely sure)
        # -> one: most up to date, but might just miss each other? probably only applicable if sensor sampling rate is vastly different from render fps?
        # -> two: always one frame behind, but might not jump then
        self._draw_state = mp.Queue(maxsize=2)

    def init_draw(self, *args, **kwargs):
        """
        Heart of the nodes drawing, should be a functional function
        """

        update_fn = self._init_draw(*args, **kwargs)

        def update():
            nonlocal update_fn
            cur_state = {}
            res = None

            try:
                cur_state = self._draw_state.get_nowait()
            except queue.Empty:
                pass
            # always execute the update, even if no new data is added, as a view might want to update not based on the self emited data
            # this happens for instance if the view wants to update based on user interaction (and not data)
            if self._should_draw(**cur_state):
                self.verbose('Decided to draw', cur_state.keys())
                res = update_fn(**cur_state)
            else:
                self.debug('Decided not to draw', cur_state.keys())

            return res

        return update

    def stop(self, children=True):
        if self._running == True:  # -> seems important as the processes otherwise not always return (especially on fast machines, seems to be a race condition somewhere, not sure i've fully understood whats happening here, but seems to work so far)
            # we need to clear the draw state, as otherwise the feederqueue never returns and the whole script never returns
            while not self._draw_state.empty():
                self._draw_state.get()

            # should throw an error if anyone tries to insert anything into the queue after we emptied it
            # also should allow the queue to be garbage collected
            # seems not be important though...
            self._draw_state.close()

            # sets _running to false
            super().stop(children)

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
        if not self._draw_state.full():
            self.verbose('Storing for draw:', kwargs.keys())
            self._draw_state.put_nowait(kwargs)
            # self.verbose('Stored for draw')

class FPS_Helper():
    def __init__(self, name):
        self.name = name
        self.n_frames = 0
        self.n_frames_total = 0
        self.report_every_x_seconds = 10
        self.timer = time.time()
        
    def count(self):
        self.n_frames += 1
        el_time = time.time() - self.timer
        if el_time > self.report_every_x_seconds:
            self.n_frames_total += self.n_frames
            print(f"Current fps: {self.n_frames / el_time:.2f} (Total frames: {self.n_frames_total}) -- {self.name}")
            self.timer = time.time()
            self.n_frames = 0

class View_MPL(View):
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

        fps = FPS_Helper(str(self))

        def update(n_frames, **kwargs):
            nonlocal update_fn, artis_storage, self, fps
            cur_state = {}

            fps.count()

            try:
                cur_state = self._draw_state.get_nowait()
            except queue.Empty:
                pass
            # always execute the update, even if no new data is added, as a view might want to update not based on the self emited data
            # this happens for instance if the view wants to update based on user interaction (and not data)
            if self._should_draw(**cur_state):
                artis_storage['returns'] = update_fn(**cur_state)
                self.verbose('Decided to draw', cur_state.keys())
            else:
                self.debug('Decided not to draw', cur_state.keys())
                    
            return artis_storage['returns']

        return update


class View_QT(View):
    def _init_draw(self, parent):
        layout = QVBoxLayout(parent)
        layout.addWidget(QLabel(str(self)))

    def init_draw(self, parent):
        """
        Heart of the nodes drawing, should be a functional function
        """
        update_fn = self._init_draw(parent=parent)

        # if there is no update function only _init_draw will be needed / called
        if update_fn is not None:
            fps = FPS_Helper(str(self))

            # TODO: figure out more elegant way to not have this blocking until new data is available...
            def update_blocking():
                nonlocal update_fn, fps
                cur_state = {}
                
                fps.count()

                try:
                    cur_state = self._draw_state.get_nowait()
                    # cur_state = self._draw_state.get(block=True, timeout=0.05)
                except queue.Empty:
                    pass

                if self._should_draw(**cur_state):
                    self.verbose('Decided to draw', cur_state.keys())
                    update_fn(**cur_state)
                    return True
                else:
                    self.debug('Decided not to draw', cur_state.keys())

                return False

            return update_blocking
        self.debug('No update function was returned, as none exists.')
        return None

class View_Vispy(View):
    def _init_draw(self, fig):
        def update(**kwargs):
            raise NotImplementedError()
        return update

    def init_draw(self, fig):
        """
        Heart of the nodes drawing, should be a functional function
        """
        update_fn = self._init_draw(fig)

        fps = FPS_Helper(str(self))

        # TODO: figure out more elegant way to not have this blocking until new data is available...
        def update_blocking():
            nonlocal update_fn, fps
            cur_state = {}
            
            fps.count()

            try:
                cur_state = self._draw_state.get_nowait()
                # cur_state = self._draw_state.get(block=True, timeout=0.05)
            except queue.Empty:
                pass

            if self._should_draw(**cur_state):
                self.verbose('Decided to draw', cur_state.keys())
                update_fn(**cur_state)
                return True
            else:
                self.debug('Decided not to draw', cur_state.keys())

            return False

        return update_blocking

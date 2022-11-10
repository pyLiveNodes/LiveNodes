import multiprocessing as mp
import queue
import time

from .node import Node
from .components.utils.reportable import Reportable


class View(Node, abstract_class=True):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: consider if/how to disable the visualization of a node?
        # self.display = display

        # TODO: evaluate if one or two is better as maxsize (the difference should be barely noticable, but not entirely sure)
        # -> one: most up to date, but might just miss each other? probably only applicable if sensor sampling rate is vastly different from render fps?
        # -> two: always one frame behind, but might not jump then
        self._draw_state = mp.Queue(maxsize=2)

    def register_reporter(self, reporter_fn):
        if hasattr(self, 'fps'):
            self.fps.register_reporter(reporter_fn)
        return super().register_reporter(reporter_fn)

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
                self.fps.count()
                return res
            else:
                self.debug('Decided not to draw', cur_state.keys())
            return res

        return update

    def stop_node(self, **kwargs):
        # we need to clear the draw state, as otherwise the feederqueue never returns and the whole script never returns
        if self._draw_state is not None:
            while not self._draw_state.empty():
                self._draw_state.get()

            # should throw an error if anyone tries to insert anything into the queue after we emptied it
            # also should allow the queue to be garbage collected
            # seems not be important though...
            self._draw_state.close()
            self._draw_state = None

        # sets _running to false
        super().stop(**kwargs)

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
        self.verbose('Storing for draw:', kwargs.keys())
        try:
            self._draw_state.put_nowait(kwargs)
        except queue.Full:
            self.debug('Could not render data, view not ready.')



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

        def update(n_frames, **kwargs):
            nonlocal update_fn, artis_storage, self
            cur_state = {}

            try:
                cur_state = self._draw_state.get_nowait()
            except queue.Empty:
                pass
            # always execute the update, even if no new data is added, as a view might want to update not based on the self emited data
            # this happens for instance if the view wants to update based on user interaction (and not data)
            if self._should_draw(**cur_state):
                self.verbose('Decided to draw', cur_state.keys())
                artis_storage['returns'] = update_fn(**cur_state)
                self.fps.count()
            else:
                self.debug('Decided not to draw', cur_state.keys())
                    
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
                cur_state = {}
                
                try:
                    cur_state = self._draw_state.get_nowait()
                except queue.Empty:
                    pass
                # always execute the update, even if no new data is added, as a view might want to update not based on the self emited data
                # this happens for instance if the view wants to update based on user interaction (and not data)
                if self._should_draw(**cur_state):
                    self.verbose('Decided to draw', cur_state.keys())
                    update_fn(**cur_state)
                    self.fps.count()
                    return True
                else:
                    self.debug('Decided not to draw', cur_state.keys())
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
            cur_state = {}
            
            try:
                cur_state = self._draw_state.get_nowait()
            except queue.Empty:
                pass
            # always execute the update, even if no new data is added, as a view might want to update not based on the self emited data
            # this happens for instance if the view wants to update based on user interaction (and not data)
            if self._should_draw(**cur_state):
                self.verbose('Decided to draw', cur_state.keys())
                update_fn(**cur_state)
                self.fps.count()
                return True
            else:
                self.debug('Decided not to draw', cur_state.keys())
            return False

        return update_blocking

import functools
from .utils.reportable import Reportable
import logging
import multiprocessing as mp
import threading
import deprecation

class Logger(Reportable):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.logger = logging.getLogger('livenodes')

    # this may be called in another thread/computer, than the init method -> cache the call and use it in prep_str
    # -> wait how would that be a problem? wouldn't the field value then be pickled (if mp.spawn) or exist (if mp.forked)?
    # -> i guess that's related to the Reportable?
    @functools.lru_cache(maxsize=1)
    def _construct_str(self):
        limit = 30
        name = str(self)
        name = name if len(name) < limit else name[:limit - 3] + '...' 
        return f"{name: <30}"

    # === Logging Stuff =================
    # TODO: move this into it's own module/file?
    def error(self, *text):
        self.logger.error(self._prep_log(*text))
        if self.logger.isEnabledFor(logging.ERROR):
            self._report(log=" ".join(str(t) for t in text))

    def warn(self, *text):
        self.logger.warn(self._prep_log(*text))
        if self.logger.isEnabledFor(logging.WARN):
            self._report(log=" ".join(str(t) for t in text))

    def info(self, *text):
        self.logger.info(self._prep_log(*text))
        if self.logger.isEnabledFor(logging.INFO):
            self._report(log=" ".join(str(t) for t in text))

    def debug(self, *text):
        self.logger.debug(self._prep_log(*text))
        if self.logger.isEnabledFor(logging.DEBUG):
            self._report(log=" ".join(str(t) for t in text))

    @deprecation.deprecated(details="Verbose will be removed, please use debug instead")
    def verbose(self, *text):
        self.logger.debug(self._prep_log(*text))
        if self.logger.isEnabledFor(logging.DEBUG):
            self._report(log=" ".join(str(t) for t in text))

    def _prep_log(self, *text):
        txt = " ".join(str(t) for t in text)
        cur_proc = mp.current_process().name
        cur_thread = threading.current_thread().name
        msg = f"HOST | {cur_proc: <13} | {cur_thread: <13} | {self._construct_str()} | {txt}"
        return msg

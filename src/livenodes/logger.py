# Print iterations progress
from distutils.log import ERROR
from enum import IntEnum
import multiprocessing as mp
import threading
import datetime


class LogLevel(IntEnum):
    ERROR = 1
    WARN = 2
    INFO = 3
    DEBUG = 4
    # DRAW = 5 # TODO: consider implementing this for the draw logs as they 
    VERBOSE = 6



class Logger():
    _log_level = LogLevel.VERBOSE
    _max_log_level = LogLevel.VERBOSE
    _lock = mp.Lock()

    cbs = {}

    def __init__(self, stdout=True, default_level=LogLevel.DEBUG):
        self._log_level = default_level
        self._max_log_level = default_level
        if stdout:
            self.register_cb(self._print, LogLevel.ERROR)

    def _print(self, msg):
        print(msg, flush=True)

    def register_cb(self, cb, log_level=None):
        if log_level is None:
            log_level = self._log_level
        
        self.cbs[cb] = log_level

        if log_level > self._max_log_level:
            self._max_log_level = log_level

    def remove_cb(self, cb):
        del self.cbs[cb]

    def error(self, *args):
        self._log(LogLevel.ERROR, *args)

    def warn(self, *args):
        self._log(LogLevel.WARN, *args)

    def info(self, *args):
        self._log(LogLevel.INFO, *args)

    def debug(self, *args):
        self._log(LogLevel.DEBUG, *args)

    def verbose(self, *args):
        self._log(LogLevel.VERBOSE, *args)

    def _log(self, level, *text):
        if level <= self._max_log_level:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %X")
            cur_proc = mp.current_process().name
            cur_thread = threading.current_thread().name
            txt = " ".join(str(t) for t in text)

            level_str = level.name.lower()

            msg = f"{timestamp} | {cur_proc: <13} | {cur_thread: <13} | {level_str: <11} | {txt}"

            # acquire blocking log
            self._lock.acquire(True)

            for cb, cb_level in self.cbs.items():
                if level <= cb_level:
                    cb(msg)

            # release log
            self._lock.release()

    def set_log_level(self, level):
        self._log_level = level


logger = Logger(stdout=True, default_level=LogLevel.DEBUG)

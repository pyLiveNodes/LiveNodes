
# Print iterations progress
from asyncore import write
from enum import IntEnum
import multiprocessing as mp
import threading
import datetime


def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()



class LogLevel(IntEnum):
    WARN = 1
    INFO = 2
    DEBUG = 3

class Logger():
    _log_level = LogLevel.INFO
    _lock = mp.Lock()

    cbs = []

    def register_cb(self, cb):
        self.cbs.append(cb)
    
    def remove_cb(self, cb):
        self.cbs.remove(cb)

    def warn(self, *args):
        self._log(LogLevel.WARN, *args)

    def info(self, *args):
        self._log(LogLevel.INFO, *args)

    def debug(self, *args):
        self._log(LogLevel.DEBUG, *args)

    def _log(self, level, *text):
        if level <= self._log_level:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %X")
            cur_proc = mp.current_process().name
            cur_thread = threading.current_thread().name
            txt = " ".join(str(t) for t in text)

            level_str = ["Warning", "Information", "Debug"][level]

            msg = f"{timestamp} | {cur_proc: <11} | {cur_thread: <11} | {level_str: <11} | {txt}"

            # acquire blocking log
            self._lock.acquire(True)

            print(msg, flush=True)
            for cb in self.cbs:
                cb(msg)
            
            # release log
            self._lock.release()

    def set_log_level(self, level):
        self._log_level = level


logger = Logger()
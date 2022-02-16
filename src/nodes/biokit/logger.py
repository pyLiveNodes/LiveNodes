
import datetime
import multiprocessing
import sys
import threading

"""
Simple logging for BioKIT

Example Usage:
>>> import logger
>>> from logger import log

Logging goes to stdout
>>> log(BioKIT.LogSeverityLevel.Information, 4, "threads working on", 8, "requests")
[2] 2014-05-23 16:48:12.336892 - MainThread  : 4 threads working on 8 requests
"""

from . import BioKIT

logger_lock = multiprocessing.Lock()


def log(level, *text):
    """
    Log text at the given level.

    Only one thread may log at any given time. Other threads will wait
    for the first thread's logging to finish before logging.

    Parameters:
        level - One of the logging levels in BioKIT.LogSeverityLevel
        text - Text to be logged. This can be anything from a simple string or
               a list to collection of strings, and numbers

               e.g. these two output the same text:
                log(BioKIT.LogSeverityLevel.Information, "No {} is first".format(2))
                log(BioKIT.LogSeverityLevel.Information, "No", 2, "is first")
    """

    if BioKIT.LoggingUtilities.getLogLevel() <= level:
        msg = "{} | {:<11} | {:<11} | {:>11} | {}".format(datetime.datetime.now().strftime("%Y-%m-%d %X"),
                                                          multiprocessing.current_process().name,
                                                          threading.current_thread().name,
                                                          str(level),
                                                          " ".join(str(t) for t in text))

        # acquire blocking log
        logger_lock.acquire(True)

        print(msg, flush=True)

        # release log
        logger_lock.release()

def warn(*text):
    log(BioKIT.LogSeverityLevel.Warning, *text)

def info(*text):
    log(BioKIT.LogSeverityLevel.Information, *text)

def debug(*text):
    log(BioKIT.LogSeverityLevel.Debug, *text)

# Integrate the C++ logging
def loggingCallback(fileName, level, message):
    log(level, fileName + ": " + message)

def set_log_level(level):
    """
    Set log level. Everything of higher level including the set level
    is logged
    - BioKIT.LogSeverityLevel.Error
    - BioKIT.LogSeverityLevel.Critical
    - BioKIT.LogSeverityLevel.Warning
    - BioKIT.LogSeverityLevel.Information
    - BioKIT.LogSeverityLevel.Debug
    - BioKIT.LogSeverityLevel.Trace (only available in BioKIT debug builds)
    """
    BioKIT.LoggingUtilities.setLogLevel(level)

# Use this logging for BioKIT C++ logging when this module is imported
BioKIT.LoggingUtilities.setLoggingCallback(loggingCallback)

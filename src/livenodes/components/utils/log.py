import logging
import traceback
import sys

# adapted from: https://superfastpython.com/multiprocessing-logging-in-python/ and
# https://stackoverflow.com/questions/641420/how-should-i-log-while-using-multiprocessing-in-python
def drain_log_queue(parent_log_queue, logger_name, stop_log_event):
    logger = logging.getLogger(logger_name)
    while not stop_log_event.is_set():
        try:
            record = parent_log_queue.get()
            logger.handle(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except EOFError:
            break
        except:
            traceback.print_exc(file=sys.stderr)
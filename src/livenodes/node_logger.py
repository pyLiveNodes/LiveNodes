from .logger import logger
from .reportable import Reportable

class Logger(Reportable):

    def error(self, *text):
        msg = self._prep_log(*text)
        self._report(log=msg)
        logger.error(msg)

    def warn(self, *text):
        msg = self._prep_log(*text)
        self._report(log=msg)
        logger.warn(msg)

    def info(self, *text):
        msg = self._prep_log(*text)
        self._report(log=msg)
        logger.info(msg)

    def debug(self, *text):
        msg = self._prep_log(*text)
        self._report(log=msg)
        logger.debug(msg)

    def verbose(self, *text):
        msg = self._prep_log(*text)
        self._report(log=msg)
        logger.verbose(msg)

    def _prep_log(self, *text):
        node = str(self)
        txt = " ".join(str(t) for t in text)
        msg = f"{node: <40} | {txt}"
        return msg

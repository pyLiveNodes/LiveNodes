from .logger import logger
from .reportable import Reportable

class Logger(Reportable):

    def error(self, *text):
        self._report(log=" ".join(str(t) for t in text))
        logger.error(self._prep_log(*text))

    def warn(self, *text):
        self._report(log=" ".join(str(t) for t in text))
        logger.warn(self._prep_log(*text))

    def info(self, *text):
        self._report(log=" ".join(str(t) for t in text))
        logger.info(self._prep_log(*text))

    def debug(self, *text):
        self._report(log=" ".join(str(t) for t in text))
        logger.debug(self._prep_log(*text))

    def verbose(self, *text):
        self._report(log=" ".join(str(t) for t in text))
        logger.verbose(self._prep_log(*text))

    def _prep_log(self, *text):
        node = str(self)
        txt = " ".join(str(t) for t in text)
        msg = f"{node: <40} | {txt}"
        return msg

from .logger import logger, LogLevel

class Logger():
    # === Logging Stuff =================
    # TODO: move this into it's own module/file?
    def error(self, *text):
        logger.error(self._prep_log(*text))

    def warn(self, *text):
        logger.warn(self._prep_log(*text))

    def info(self, *text):
        logger.info(self._prep_log(*text))

    def debug(self, *text):
        logger.debug(self._prep_log(*text))

    def verbose(self, *text):
        logger.verbose(self._prep_log(*text))

    def _prep_log(self, *text):
        node = str(self)
        txt = " ".join(str(t) for t in text)
        msg = f"{node: <40} | {txt}"
        return msg

from .utils.logger import logger, LogLevel
import functools

class Logger():
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    # this may be called in another thread/computer, than the init method -> cache the call and use it in prep_str
    @functools.lru_cache(maxsize=1)
    def _construct_str(self):
        limit = 30
        name = str(self)
        name = name if len(name) < limit else name[:limit - 3] + '...' 
        return f"{name: <30}"

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
        txt = " ".join(str(t) for t in text)
        msg = f"{self._construct_str()} | {txt}"
        return msg

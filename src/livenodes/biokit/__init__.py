
# === BioKIT import ================================================
from .biokit import BioKIT

from livenodes.core.logger import logger as node_logger


def loggingCallback(fileName, level, message):
    node = "BioKIT"
    txt = f'BioKIT.{str(level)} -- {fileName}: {message}'
    msg = f"{node: <40} | {txt}"
    node_logger.debug(msg)

BioKIT.LoggingUtilities.setLoggingCallback(loggingCallback) #<- this seems to be ignored atm... :/
BioKIT.LoggingUtilities.setLogLevel(BioKIT.LogSeverityLevel.Information)
        
# use this for debugging
# logger.set_log_level(BioKIT.LogSeverityLevel.Debug)


# === Node Registry ================================================
from class_registry import ClassRegistry

local_registry = ClassRegistry('__name__')

from os.path import dirname, basename, isfile, join
import glob

modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [
    basename(f)[:-3] for f in modules
    if isfile(f) and not f.endswith('__init__.py')
]
print(__all__)

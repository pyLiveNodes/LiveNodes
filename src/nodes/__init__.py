import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'biokitPython')))

import recognizer
import logger
import BioKIT

logger.set_log_level(BioKIT.LogSeverityLevel.Warning)

# use this for debugging
# logger.set_log_level(BioKIT.LogSeverityLevel.Debug)

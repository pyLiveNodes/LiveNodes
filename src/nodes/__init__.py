# import os
# import sys
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'biokitPython')))

from .biokit import BioKIT, logger

logger.set_log_level(BioKIT.LogSeverityLevel.Warning)

# use this for debugging
# logger.set_log_level(BioKIT.LogSeverityLevel.Debug)


# Sniff out the correct plux api for this platform
import platform
import sys

# TODO: test, clean and extend this, currently arm32 is not checked
osDic = {"Darwin": "MacOS",
         "Linux": "Linux64",
         "Windows":("Win32_37","Win64_37")}
if platform.system() != "Windows":
    if platform.machine() == 'aarch64':
        path = f"plux-api/LinuxARM64_38"
    else:
        path = f"plux-api/{osDic[platform.system()]}"
else:
    if platform.architecture()[0] == '64bit':
        path = "plux-api/Win64_37"
    else:
        path = "plux-api/Win32_37"

print('Using Plux:', path)
sys.path.append(f"src/nodes/{path}")
# sys.path.append(path)
# print(sys.path)
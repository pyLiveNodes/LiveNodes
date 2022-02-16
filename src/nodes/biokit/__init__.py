# Sniff out the correct biokit shared object for this platform
import platform
import sys

# TODO: test, clean and extend this, currently arm32 is not checked
osDic = {"Darwin": "MacOS",
         "Linux": "Linux64",
         "Windows":("Win32_37","Win64_37")}
if platform.system() != "Windows":
    if platform.machine() == 'aarch64':
        path = f"lib/LinuxARM64_38"
    else:
        path = f"lib/{osDic[platform.system()]}"
else:
    if platform.architecture()[0] == '64bit':
        path = "lib/Win64_37"
    else:
        path = "lib/Win32_37"

print('Using BioKIT:', path)
sys.path.append(f"src/nodes/biokit/{path}")
# sys.path.append(path)
# print(sys.path)

import BioKIT
# Sniff out the correct biokit shared object for this platform
import platform
import sys
import os

# TODO: test, clean and extend this, currently arm32 is not checked
osDic = {"Darwin": "MacOS",
         "Linux": "Linux64",
         "Windows":("Win32_37","Win64_37")}
if platform.system() != "Windows":
    if platform.machine() == 'aarch64':
        path = f"lib/LinuxARM64_38"
    else:
        path = f"lib/{osDic[platform.system()]}"
# else:
#     if platform.architecture()[0] == '64bit':
#         path = "lib/Win64_37"
#     else:
#         path = "lib/Win32_37"

full_path = os.path.join(os.path.dirname(__file__), path)
print('Using BioKIT:', full_path)
sys.path.append(full_path)


import BioKIT

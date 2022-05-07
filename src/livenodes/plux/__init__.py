import os

# Sniff out the correct plux api for this platform
import platform
import sys

# TODO: test, clean and extend this, currently arm32 is not checked
osDic = {
    "Darwin": "MacOS",
    "Linux": "Linux64",
    "Windows": ("Win32_37", "Win64_37")
}
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

full_path = os.path.join(os.path.dirname(__file__), path)
print('Using Plux:', full_path)
sys.path.append(full_path)


from class_registry import ClassRegistry
local_registry = ClassRegistry('__name__')

from os.path import dirname, basename, isfile, join
import glob
modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]
print(__all__)

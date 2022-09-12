from .registry import Register
# There is one one global registry of nodes
# In order to not have circular dependencies, but allow for global modification (ie adding classes, enabling/disabling packages)
# this registry is only created the first an instance is needed and then stored for subsequent configs etc
REGISTRY = None

def get_registry():
    global REGISTRY
    if REGISTRY is None:
        REGISTRY = Register()
    return REGISTRY




from .node import Node
from .components.bridges import Location
from .graph import Graph
from .viewer import View
from .components.utils.logger import logger

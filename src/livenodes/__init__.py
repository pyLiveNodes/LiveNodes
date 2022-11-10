from .registry import Register
# There is one one global registry of nodes
# In order to not have circular dependencies, but allow for global modification (ie adding classes, enabling/disabling packages)
# this registry is only created the first an instance is needed and then stored for subsequent configs etc
REGISTRY = Register()

def get_registry():
    global REGISTRY
    if not REGISTRY.collected_installed:
        REGISTRY.collect_installed()
    return REGISTRY




from .node import Node
from .graph import Graph
from .viewer import View
from .producer import Producer

from .registry import Node_Register

# There is one one global registry of nodes
# In order to not have circular dependencies, but allow for global modification (ie adding classes, enabling/disabling packages)
# this registry is only created the first an instance is needed and then stored for subsequent configs etc
REGISTRY = None

def get_registry():
    global REGISTRY
    if REGISTRY is None:
        REGISTRY = Node_Register()
    return REGISTRY
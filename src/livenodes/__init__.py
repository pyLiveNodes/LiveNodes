from .registry import Register
# There is one one global registry of nodes
# In order to not have circular dependencies, but allow for global modification (ie adding classes, enabling/disabling packages)
# this registry is only created the first an instance is needed and then stored for subsequent configs etc
REGISTRY = Register()

def get_registry():
    """Get the global registry instance."""
    return REGISTRY

from .node import Node
from .graph import Graph
from .viewer import View
from .producer import Producer
from .producer_async import Producer_async
from .components.connection import Connection
from .components.node_connector import Attr
from .components.port import Port, Ports_collection


from .components.bridges import Bridge_local, Bridge_thread, Bridge_process, Bridge_aioprocessing
REGISTRY.bridges.register('Bridge_local', Bridge_local)
REGISTRY.bridges.register('Bridge_thread', Bridge_thread)
REGISTRY.bridges.register('Bridge_process', Bridge_process)
# REGISTRY.bridges.register('Bridge_aioprocessing', Bridge_aioprocessing)

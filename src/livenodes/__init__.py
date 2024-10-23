from .registry import Register
# There is one one global registry of nodes
# In order to not have circular dependencies, but allow for global modification (ie adding classes, enabling/disabling packages)
# this registry is only created the first an instance is needed and then stored for subsequent configs etc
REGISTRY = Register()

import logging
logger = logging.getLogger('livenodes')

def get_registry():
    logger.warning('retrieving registry')
    global REGISTRY
    if not REGISTRY.collected_installed:
        # --- first hook up the default briges
        from .components.bridges import Bridge_local, Bridge_thread, Bridge_process
        logger.warning('registering default bridges')
        REGISTRY.bridges.register('Bridge_local', Bridge_local)
        REGISTRY.bridges.register('Bridge_thread', Bridge_thread)
        REGISTRY.bridges.register('Bridge_process', Bridge_process)
        from .components.bridges import Bridge_thread_aio, Bridge_process_aio
        REGISTRY.bridges.register('Bridge_thread_aio', Bridge_thread_aio)
        REGISTRY.bridges.register('Bridge_process_aio', Bridge_process_aio)

        # --- now collect all installed packages
        REGISTRY.collect_installed()

    return REGISTRY


from .node import Node
from .graph import Graph
from .viewer import View
from .producer import Producer
from .producer_async import Producer_async
from .components.connection import Connection
from .components.node_connector import Attr
from .components.port import Port, Ports_collection
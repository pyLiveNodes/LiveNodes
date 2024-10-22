from functools import partial
from class_registry import ClassRegistry
from class_registry.entry_points import EntryPointClassRegistry

import importlib, sys
import logging
logger = logging.getLogger('livenodes')


## Monkey patch registry so that we can report progress
import typing
from importlib.metadata import entry_points
T = typing.TypeVar("T")
def _get_cache(self) -> dict[typing.Hashable, typing.Type[T]]:
        """
        Populates the cache (if necessary) and returns it.
        """
        if self._cache is None:
            self._cache = {}
            entries = entry_points(group=self.group)
            for i, e in enumerate(entries):
                if hasattr(self, 'report_progress'):
                    self.report_progress(e.name, i, len(entries))
                cls = e.load()

                # Try to apply branding, but only for compatible types (i.e., functions
                # and methods can't be branded this way).
                if self.attr_name and isinstance(cls, type):
                    setattr(cls, self.attr_name, e.name)

                self._cache[e.name] = cls

        return self._cache

EntryPointClassRegistry._get_cache = _get_cache
## End monkey patch

class Register():
    def __init__(self):
        self.nodes = Entrypoint_Register(entrypoints='livenodes.nodes')
        self.bridges = Entrypoint_Register(entrypoints='livenodes.bridges')

        self.collected_installed = False
        # I don't think we need the registry for ports, as these are imported via the nodes classes anyway
        # self.ports = Entrypoint_Register(entrypoints='livenodes.ports')

    def collect_installed(self):
        logger.debug('Collecting installed Packages')

        if not self.collected_installed:
            self.nodes.collect_installed()
            self.bridges.collect_installed()
            self.collected_installed = True

        # TODO: check if there is a more elegant way to access the number of installed classes
        logger.info(f'Collected installed Nodes ({len(list(self.nodes.values()))})') 
        logger.info(f'Collected installed Bridges ({len(list(self.bridges.values()))})')
    
    def installed_packages(self):
        packages = []
        for item in self.nodes.values():
            packages.append(item.__module__.split('.')[0])
        for item in self.bridges.values():
            packages.append(item.__module__.split('.')[0])
        return list(dict.fromkeys(packages)) # works because form 3.7 dict insertion order is preserved (as opposed to sets)

    def reload(self, invalidate_caches=False):
        logger.debug('Reloading modules')
        if invalidate_caches:
            importlib.invalidate_caches()
            
        # Check for new nodes since last time
        self.collected_installed = False
        self.collect_installed()

        # Now let's reload all modules of the classes that we have
        # ie because some nodes might not be loaded via entrypoints but for instance via the decorator or register call directly
        modules_to_reload = set()
        
        for item in self.nodes.values():
            module_name = item.__module__
            modules_to_reload.add(module_name)

        for item in self.bridges.values():
            module_name = item.__module__
            modules_to_reload.add(module_name)

        for module_name in modules_to_reload:
            try:
                if invalidate_caches and module_name in sys.modules:
                    del sys.modules[module_name]
                    
                module = importlib.import_module(module_name)
                importlib.reload(module)
                logger.info(f'Reloaded module: {module_name}')
            except ModuleNotFoundError:
                logger.warning(f'Module not found: {module_name}')
            except Exception as e:
                logger.error(f'Error reloading module {module_name}: {e}')

        logger.debug('Reloading complete')

    def package_enable(self, package_name):
        raise NotImplementedError()

    def package_disable(self, package_name):
        raise NotImplementedError()
    
    def register_callback(self, fn):
        self.nodes.register_callback(fn)
        self.bridges.register_callback(fn)
    
    def deregister_callback(self, fn):
        self.nodes.deregister_callback(fn)
        self.bridges.deregister_callback(fn)

# yes, this basically just wraps the ClassRegistry, but i am contemplating namespacing the local_registries
# and also allows to merge local registries or classes (currently only used in a test case, but the scenario of registering a class outside of a package is still valid)
class Entrypoint_Register():

    def __init__(self, entrypoints):
        # create local registry
        self.reg = ClassRegistry()
        self.entrypoints = entrypoints
        self.callbacks = []
        
    def collect_installed(self):
        # load all findable packages
        self.installed_packages = EntryPointClassRegistry(self.entrypoints)
        self.installed_packages.report_progress = partial(self.trigger_callback('Discovering Entrypoints'))
        self.add_register(self.installed_packages)

    def add_register(self, register):
        for key in register.keys():
            self.register(key=key.lower(), class_=register.get_class(key))

    def decorator(self, cls):
        self.register(key=cls.__name__.lower(), class_=cls)
        return cls

    def register(self, key, class_):
        self.trigger_callback('Registering Class', key, None, None)
        return self.reg.register(key.lower())(class_)

    def get(self, key, *args, **kwargs):
        return self.reg.get(key.lower(), *args, **kwargs)

    def values(self):
        return self.reg.classes()
    
    def trigger_callback(self, context, name, i, total):
        for fn in self.callbacks:
            fn(context, name, i, total)
    
    def register_callback(self, fn):
        self.callbacks.append(fn)

    def deregister_callback(self, fn):
        self.callbacks.remove(fn)


if __name__ == "__main__":
    r = Register()
    r.collect_installed()
    from livenodes.components.bridges import Bridge_local, Bridge_thread, Bridge_process
    r.bridges.register('Bridge_local', Bridge_local)
    # print(list(r.bridges.reg.keys()))
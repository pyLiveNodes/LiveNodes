from class_registry import ClassRegistry
from class_registry.entry_points import EntryPointClassRegistry

import importlib, sys
import logging
logger = logging.getLogger('livenodes')


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

# yes, this basically just wraps the ClassRegistry, but i am contemplating namespacing the local_registries
# and also allows to merge local registries or classes (currently only used in a test case, but the scenario of registering a class outside of a package is still valid)
class Entrypoint_Register():

    def __init__(self, entrypoints):
        # create local registry
        self.reg = ClassRegistry()
        self.entrypoints = entrypoints
        
    def collect_installed(self):
        # load all findable packages
        self.installed_packages = EntryPointClassRegistry(self.entrypoints)
        self.add_register(self.installed_packages)

    def add_register(self, register):
        for key in register.keys():
            self.register(key=key.lower(), class_=register.get_class(key))

    def decorator(self, cls):
        self.register(key=cls.__name__.lower(), class_=cls)
        return cls

    def register(self, key, class_):
        logger.debug(f'Registered: {key} -> {class_}')
        return self.reg.register(key.lower())(class_)

    def get(self, key, *args, **kwargs):
        return self.reg.get(key.lower(), *args, **kwargs)

    def values(self):
        return self.reg.classes()
    

if __name__ == "__main__":
    r = Register()
    r.collect_installed()
    from livenodes.components.bridges import Bridge_local, Bridge_thread, Bridge_process
    r.bridges.register('Bridge_local', Bridge_local)
    # print(list(r.bridges.reg.keys()))
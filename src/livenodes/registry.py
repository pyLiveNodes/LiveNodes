from importlib.metadata import entry_points, EntryPoint
import importlib, sys
import logging
logger = logging.getLogger('livenodes')

class Register():
    def __init__(self, lazy_load=False):
        self.nodes = Entrypoint_Register(entrypoints='livenodes.nodes', lazy_load=lazy_load)
        self.bridges = Entrypoint_Register(entrypoints='livenodes.bridges', lazy_load=lazy_load)

    def installed_packages(self):
        packages = []
        for item in self.nodes.values():
            packages.append(item.__module__.split('.')[0])
        for item in self.bridges.values():
            packages.append(item.__module__.split('.')[0])
        return list(dict.fromkeys(packages)) # works because form 3.7 dict insertion order is preserved (as opposed to sets)

    def reload(self, invalidate_caches=False):
        logger.debug('Reloading modules')            
        self.nodes.reload(invalidate_caches)
        self.bridges.reload(invalidate_caches)
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


class Entrypoint_Register():
    def __init__(self, entrypoints, lazy_load=True):
        # create local registry
        self.entrypoints = entrypoints
        self.callbacks = []
        self.manually_registered = {}  # manually registered classes
        self.lazy_load = lazy_load
        
        self._reset_cache()

        if not self.lazy_load:
            # collect all installed packages immediately
            self.collect_installed()

    def _reset_cache(self):
        self.trigger_callback(f'Discovering entrypoints for {self.entrypoints}', None, None, None)
        # reset the cache and merge manually registered classes
        self.cache = self.manually_registered.copy()
        self.cache.update({val.name: val for val in entry_points(group=self.entrypoints)})

    def reload(self, invalidate_caches=False):
        self._reset_cache()

        if not self.lazy_load:
            # collect all installed packages immediately
            self.collect_installed()
            
        if invalidate_caches:
            importlib.invalidate_caches()
        modules_to_reload = []
        for item in self.cache.values():
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

    def collect_installed(self):
        for i, key in enumerate(self.cache.keys()):
            self.trigger_callback('Registering Class', key, i, len(self.cache))
            self.get_class(key)

    def decorator(self, cls):
        self.register(cls.__name__.lower(), cls)
        return cls
    
    def register(self, key, cls):
        self.manually_registered[key] = cls
        self.cache[key] = cls
    
    def get_class(self, key):
        if type(self.cache[key]) is EntryPoint:
            try:
                # load the entrypoint class
                self.cache[key] = self.cache[key].load()
            except Exception as e:
                logger.error(f'Error loading entrypoint {key}: {e}')
        return self.cache[key]

    def get(self, key, *args, **kwargs):
        return self.get_class(key.lower())(*args, **kwargs)

    def values(self):
        return self.cache.values()
    
    def trigger_callback(self, context, name, i, total):
        for fn in self.callbacks:
            fn(context, name, i, total)
    
    def register_callback(self, fn):
        self.callbacks.append(fn)

    def deregister_callback(self, fn):
        self.callbacks.remove(fn)


if __name__ == "__main__":
    r = Register()
    from livenodes.components.bridges import Bridge_local, Bridge_thread, Bridge_process
    r.bridges.register('Bridge_local', Bridge_local)
    # print(list(r.bridges.reg.keys()))
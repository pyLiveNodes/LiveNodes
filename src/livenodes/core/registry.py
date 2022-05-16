from class_registry import ClassRegistry
import importlib

# yes, this basically just wraps the ClassRegistry, but i am contemplating namespacing the local_registries
# and also allows to merge local registries
class Node_Register():

    def __init__(self):
        self.packages = ClassRegistry('__name__')

    def add_register(self, register):
        for key, val in register.items():
            self.register(key=key, class_=val)

    def register(self, key, class_):
        return self.packages._register(key=key, class_=class_)

    def get(self, key, *args, **kwargs):
        return self.packages.get(key, *args, **kwargs)

    def collect_modules(self, modules=[]):
        for p in modules:
            m = importlib.import_module(p)
            for m_name in m.__dict__["__all__"]:
                # just to load the file from the module to get it registered
                importlib.import_module(f"{p}.{m_name}")
            self.add_register(m.local_registry)

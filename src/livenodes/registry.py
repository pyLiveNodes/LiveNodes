from class_registry import ClassRegistry, EntryPointClassRegistry

# yes, this basically just wraps the ClassRegistry, but i am contemplating namespacing the local_registries
# and also allows to merge local registries or classes (currently only used in a test case, but the scenario of registering a class outside of a package is still valid)
class Node_Register():

    def __init__(self):
        # create local registry
        self.packages = ClassRegistry('__name__')
        
        # load all findable packages
        self.installed_packages = EntryPointClassRegistry('livenodes.nodes')
        self.add_register(self.installed_packages)

    def add_register(self, register):
        for key, val in register.items():
            self.register(key=key, class_=val)

    def register(self, key, class_):
        return self.packages._register(key=key, class_=class_)

    def get(self, key, *args, **kwargs):
        return self.packages.get(key, *args, **kwargs)

    def package_enable(self, package_name):
        raise NotImplementedError()

    def package_disable(self, package_name):
        raise NotImplementedError()
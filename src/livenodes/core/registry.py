from class_registry import ClassRegistry


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

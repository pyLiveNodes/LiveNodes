from livenodes import get_registry
import importlib

DEPRECATION_MODULES = []


class TestProcessing:

    def test_reloadable(self):
        r = get_registry()

        node_class = list(r.nodes.values())[0]
        module = importlib.import_module(node_class.__module__)
        module.np = True
        assert str(node_class) == "<class 'tests.utils.SimpleNode'>', group='livenodes.nodes')", "Update the test, some env/params changed and we have an unexpected class"
        assert module.np, "The class attribute should now be set"

        node_class = list(r.nodes.values())[0]
        module = importlib.import_module(node_class.__module__)
        assert str(node_class) == "<class 'tests.utils.SimpleNode'>', group='livenodes.nodes')", "Update the test, some env/params changed and we have an unexpected class"
        assert type(module.np) == bool and module.np, "Value should still be set, as it techincally is the same class"

        # invalidate_caches is only required for this test, such that the reload works (as the module itself does not change in between and thus is cached)
        r.reload(invalidate_caches=True)
        node_class = list(r.nodes.values())[0]
        module = importlib.import_module(node_class.__module__)
        assert str(node_class) == "<class 'tests.utils.SimpleNode'>', group='livenodes.nodes')", "Update the test, some env/params changed and we have an unexpected class"
        assert type(module.np) != bool, "Now the class was reloaded, so the attribute should not be set anymore"


if __name__ == "__main__":
    r = get_registry()
    node_class = list(r.nodes.values())[0]
    module = importlib.import_module(node_class.__module__)
    r.reload(invalidate_caches=True)
    # print(node_class)

    # import sys
    # module_name = node_class.__module__
    # if module_name in sys.modules:
    #     del sys.modules[module_name]
    # importlib.invalidate_caches()
    # importlib.reload(importlib.import_module(module_name))

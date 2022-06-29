from livenodes import get_registry


class TestNodeOperations():

    def test_entrypoint_discovery(self):
        # hacky way of checking if registry works
        # hacky -> because we depend on livenodes_basic_nodes for this test and i'd prefer if we wouldn't
        from livenodes_basic_nodes.math_floor import Math_floor
        assert isinstance(get_registry().get('math_floor'), Math_floor)
        
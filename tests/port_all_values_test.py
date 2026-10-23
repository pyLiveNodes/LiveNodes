from livenodes.components.port import ALL_VALUES, Port


def _make_port(name, values):
    class P(Port):
        example_values = values

        @classmethod
        def check_value(cls, value):
            return True, None
    P.__name__ = name
    return P


def test_new_values_are_appended_in_order_by_identity():
    a, b = object(), object()
    n = len(ALL_VALUES)
    _make_port("OrderPort", [a, b])
    assert ALL_VALUES[n:] == [a, b]
    assert ALL_VALUES[n] is a and ALL_VALUES[n + 1] is b


def test_known_values_are_not_appended_again():
    a = object()
    _make_port("FirstPort", [a])
    n = len(ALL_VALUES)
    _make_port("SecondPort", [a])
    assert len(ALL_VALUES) == n


def test_duplicate_reference_within_one_class_is_kept_twice():
    # the id snapshot is taken once before the loop (as before the set change), so a value listed twice
    # in the same class is appended twice
    x = object()
    n = len(ALL_VALUES)
    _make_port("DupPort", [x, x])
    assert ALL_VALUES[n:] == [x, x]


def test_port_any_examples_are_all_values():
    from ln_ports import Port_Any
    assert Port_Any.example_values is ALL_VALUES

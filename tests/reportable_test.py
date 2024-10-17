import pytest
from livenodes.components.utils.reportable import Reportable

def test_register_reporter():
    reportable = Reportable()
    def dummy_reporter(**kwargs):
        pass

    reportable.register_reporter(dummy_reporter)
    assert dummy_reporter in reportable.reporters, "Reporter should be registered"

def test_deregister_reporter():
    reportable = Reportable()
    def dummy_reporter(**kwargs):
        pass

    reportable.register_reporter(dummy_reporter)
    reportable.deregister_reporter(dummy_reporter)
    assert dummy_reporter not in reportable.reporters, "Reporter should be deregistered"

def test_deregister_nonexistent_reporter():
    reportable = Reportable()
    def dummy_reporter(**kwargs):
        pass

    with pytest.raises(ValueError, match="Reporter function not found in list."):
        reportable.deregister_reporter(dummy_reporter)

def test_report():
    reportable = Reportable()
    results = []

    def dummy_reporter(**kwargs):
        results.append(kwargs)

    reportable.register_reporter(dummy_reporter)
    reportable._report(test_key="test_value")
    assert len(results) == 1, "Reporter should be called once"
    assert results[0] == {"test_key": "test_value"}, "Reporter should receive correct arguments"

if __name__ == "__main__":
    pytest.main()
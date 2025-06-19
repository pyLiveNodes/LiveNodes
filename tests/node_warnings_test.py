import pytest
from tests.utils import Data

class TestWarnings():

    def test_nonexisting_port(self):
        data = Data(name="A", compute_on="")
        with pytest.raises(ValueError):
            data._emit_data(data=[], channel='nonexistantportname')
import pytest
from livenodes import Producer, Ports_collection
from .utils import Port_Ints

class Ports_none(Ports_collection): 
    pass

class Ports_simple(Ports_collection):
    alternate_data: Port_Ints = Port_Ints("Alternate Data")

class Data(Producer):
    ports_in = Ports_none()
    # yes, "Data" would have been fine, but wanted to quickly test the naming parts
    # TODO: consider
    ports_out = Ports_simple()

    def _run(self):
        for ctr in range(10):
            self.info(ctr)
            yield self.ret(alternate_data=ctr)


class TestWarnings():

    def test_nonexisting_port(self):
        data = Data(name="A", compute_on="")
        with pytest.raises(ValueError):
            data._emit_data(data=[], channel='nonexistantportname')
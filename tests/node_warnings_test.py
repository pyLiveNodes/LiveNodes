import time
import pytest
import multiprocessing as mp

from livenodes import Node, Producer, Graph, get_registry

from typing import NamedTuple
from .utils import Port_Ints

class Ports_none(NamedTuple): 
    pass

class Ports_simple(NamedTuple):
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
        with pytest.raises(ValueError):
            data = Data(name="A", compute_on="")
            data._emit_data(data=[], channel='nonexistantportname')
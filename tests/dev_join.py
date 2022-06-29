import multiprocessing as mp

from livenodes.node import Node, Location
from livenodes.sender import Sender


class Data(Sender):
    channels_in = []
    # yes, "Data" would have been fine, but wanted to quickly test the naming parts
    # TODO: consider
    channels_out = ["Alternate Data"]

    def _run(self):
        for ctr in range(10):
            self.info(ctr)
            self._emit_data(ctr, channel="Alternate Data")
            yield ctr < 9


class Quadratic(Node):
    channels_in = ["Alternate Data"]
    channels_out = ["Alternate Data"]

    def process(self, alternate_data, **kwargs):
        self._emit_data(alternate_data**2, channel="Alternate Data")


class Save(Node):
    channels_in = ["Alternate Data"]
    channels_out = []

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.out = mp.SimpleQueue()

    def process(self, alternate_data, **kwargs):
        self.out.put(alternate_data)

    def get_state(self):
        res = []
        while not self.out.empty():
            res.append(self.out.get())
        return res



def create_simple_graph():
    data = Data(name="A", compute_on=Location.SAME, block=True)
    quadratic = Quadratic(name="B", compute_on=Location.SAME)
    out1 = Save(name="C", compute_on=Location.SAME)
    out2 = Save(name="D", compute_on=Location.SAME)

    out1.connect_inputs_to(data)
    quadratic.connect_inputs_to(data)
    out2.connect_inputs_to(quadratic)

    return data, quadratic, out1, out2

    
def test_calc_join(create_simple_graph):
    data, quadratic, out1, out2 = create_simple_graph

    data.start(join=True)
    data.stop()

    assert out2.get_state() == list(map(lambda x: x**2, range(10)))


if __name__ == "__main__":
    test_calc_join(create_simple_graph())
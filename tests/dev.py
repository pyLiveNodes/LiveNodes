import numpy as np
import multiprocessing as mp

import logging

from livenodes import Node, Producer, Graph, get_registry, Port, Ports_collection

from livenodes.components.port import Port

class Port_Ints(Port):

    example_values = [
        0, 1, 20, -15
    ]

    @classmethod
    def check_value(cls, value):
        if type(value) != int:
            return False, f"Should be int; got: {type(value)}."
        return True, None

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

class Quadratic(Node):
    ports_in = Ports_simple()
    ports_out = Ports_simple()

    def process(self, alternate_data, **kwargs):
        return self.ret(alternate_data=alternate_data**2)

class Save(Node):
    ports_in = Ports_simple()
    ports_out = Ports_none()

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.out = mp.SimpleQueue()

    def process(self, alternate_data, **kwargs):
        self.debug('re data', alternate_data)
        self.out.put(alternate_data)

    def get_state(self):
        res = []
        while not self.out.empty():
            res.append(self.out.get())
        return res


if __name__ == "__main__":
    logging.basicConfig(format='%(name)s | %(levelname)s | %(message)s', level=logging.DEBUG)

    # Processing test
    mixed = True
    if mixed:
        data = Data(name="A", compute_on="1")
        quadratic = Quadratic(name="B", compute_on="1:1")
        out1 = Save(name="C", compute_on="")
        out2 = Save(name="D", compute_on="")
    else:
        data = Data(name="A", compute_on="1")
        quadratic = Quadratic(name="B", compute_on="1")
        out1 = Save(name="C", compute_on="1")
        out2 = Save(name="D", compute_on="1")

    out1.connect_inputs_to(data)
    quadratic.connect_inputs_to(data)
    out2.connect_inputs_to(quadratic)

    g = Graph(start_node=data)
    g.start_all()
    g.join_all()
    g.stop_all()
    print('finished graph')

    # print(out1.get_state())
    # print(out2.get_state())
    # data, quadratic, out1, out2, g = None, None, None, None, None
    # time.sleep(1)
    # # print('Finished Test')


    # Same name test
    # node_a = SimpleNode(name="A")
    # node_b = SimpleNode(name="B")
    # node_c = SimpleNode(name="B")

    # node_b.connect_inputs_to(node_a)
    # node_c.connect_inputs_to(node_a)
    # # print('Finished Test')

    

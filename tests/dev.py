import numpy as np
import multiprocessing as mp

import logging
logging.basicConfig(level=logging.DEBUG)

from livenodes import Node, Producer, Graph, get_registry, Port, Ports_collection

registry = get_registry()

class Port_Data(Port):

    example_values = [np.array([[[1]]])]

    @classmethod
    def check_value(cls, value):
        if not isinstance(value, np.ndarray):
            return False, "Should be numpy array;"
        elif len(value.shape) != 3:
            return False, "Shape should be of length three (Batch, Time, Channel)"
        return True, None


class Ports_simple(Ports_collection):
    data: Port_Data = Port_Data("Data")

@registry.nodes.decorator
class SimpleNode(Node):
    ports_in = Ports_simple()
    ports_out = Ports_simple()


class Port_Data(Port):

    example_values = [np.array([[[1]]])]

    @classmethod
    def check_value(cls, value):
        if not isinstance(value, np.ndarray):
            return False, "Should be numpy array;"
        elif len(value.shape) != 3:
            return False, "Shape should be of length three (Batch, Time, Channel)"
        return True, None


class Ports_none(Ports_collection): 
    pass

class Ports_simple(Ports_collection):
    alternate_data: Port_Data = Port_Data("Alternate Data")

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
        self.error('re data', alternate_data)
        self.out.put(alternate_data)

    def get_state(self):
        res = []
        while not self.out.empty():
            res.append(self.out.get())
        return res


if __name__ == "__main__":
    # Processing test
    mixed = True
    if mixed:
        data = Data(name="A", compute_on="1:2")
        quadratic = Quadratic(name="B", compute_on="2:1")
        out1 = Save(name="C", compute_on="1:1")
        out2 = Save(name="D", compute_on="1")
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

    

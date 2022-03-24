from src.nodes.node_v2 import Sender, Node, Location
import json
import time
import multiprocessing as mp

class Data(Sender):
    channels_in = []
    channels_out = ["Data"]

    def run(self):
        for i in range(10):
            self._log(i)
            self._emit_data(i)
            yield True
        return False

class Quadratic(Node):
    channels_in = ["Data"]
    channels_out = ["Data"]

    def _should_process(self, **kwargs):
        return 'Data' in kwargs

    def process(self, Data):
        self._emit_data(Data ** 2)


class Save(Node):
    channels_in = ["Data"]
    channels_out = []

    def __init__(self, name, compute_on=Location.SAME, should_time=False):
        super().__init__(name, compute_on, should_time)
        self.out = mp.SimpleQueue()

    def _should_process(self, **kwargs):
        # print(str(self), kwargs)
        return 'Data' in kwargs

    def process(self, Data):
        # print(str(self), Data)
        self.out.put(Data)

    def get_state(self):
        res = []
        while not self.out.empty():
            res.append(self.out.get())
        return res

if __name__ == "__main__":
    data = Data(name="A", compute_on=Location.THREAD)
    quadratic = Quadratic(name="B", compute_on=Location.PROCESS)
    out1 = Save(name="C", compute_on=Location.SAME)
    out2 = Save(name="D", compute_on=Location.THREAD)
    
    out1.connect_inputs_to(data)
    quadratic.connect_inputs_to(data)
    out2.connect_inputs_to(quadratic)

    data.start()
    data.stop()

    print(out1.get_state())
    print(out2.get_state())
from src.nodes.node import Sender, Node, Location
import multiprocessing as mp

class Data(Sender):
    channels_in = []
    channels_out = ["Data"]

    def _run(self):
        for ctr in range(10):
            self.info(ctr)
            self._emit_data(ctr)
            yield ctr < 9

class Quadratic(Node):
    channels_in = ["Data"]
    channels_out = ["Data"]

    def process(self, data, **kwargs):
        self._emit_data(data ** 2)


class Save(Node):
    channels_in = ["Data"]
    channels_out = []

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self.out = mp.SimpleQueue()

    def process(self, data, **kwargs):
        self.out.put(data)

    def get_state(self):
        res = []
        while not self.out.empty():
            res.append(self.out.get())
        return res

if __name__ == "__main__":
    data = Data(name="A", compute_on=Location.THREAD, block=True)
    quadratic = Quadratic(name="B", compute_on=Location.THREAD)
    out1 = Save(name="C", compute_on=Location.THREAD)
    out2 = Save(name="D", compute_on=Location.THREAD)
    
    out1.connect_inputs_to(data)
    quadratic.connect_inputs_to(data)
    out2.connect_inputs_to(quadratic)

    data.start()
    data.join()
    data.stop()

    print(out1.get_state())
    print(out2.get_state())
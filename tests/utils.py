from livenodes import Node, Producer, Ports_collection, Producer_async
import asyncio
from livenodes.components.port import Port
from livenodes import get_registry
import multiprocessing as mp
registry = get_registry()

class Port_Ints(Port):

    example_values = [
        0, 1, 20, -15
    ]

    @classmethod
    def check_value(cls, value):
        if type(value) != int:
            return False, f"Should be int; got: {type(value)}."
        return True, None

class Port_Str(Port):
    example_values = [
        "Some example value",
        "another_one"
    ]

    @classmethod
    def check_value(cls, value):
        if type(value) != str:
            return False, f"Should be string; got {type(value)}."
        return True, None
    


class Ports_none(Ports_collection): 
    pass

class Ports_simple(Ports_collection):
    data: Port_Ints = Port_Ints("Data")

@registry.nodes.decorator
class SimpleNode(Node):
    ports_in = Ports_simple()
    ports_out = Ports_simple()

@registry.nodes.decorator
class Data(Producer):
    ports_in = Ports_none()
    # yes, "Data" would have been fine, but wanted to quickly test the naming parts
    # TODO: consider
    ports_out = Ports_simple()

    def _run(self):
        for ctr in range(10):
            self.info(ctr)
            yield self.ret(data=ctr)

@registry.nodes.decorator
class Data_failing(Producer_async):
    ports_in = Ports_none()
    ports_out = Ports_simple()

    async def _async_run(self):
        for ctr in range(10):
            self.info(ctr)
            yield self.ret(data=ctr)
            await asyncio.sleep(0)
            if ctr == 5:
                raise ValueError('Test error')


@registry.nodes.decorator
class Save(Node):
    ports_in = Ports_simple()
    ports_out = Ports_none()

    def __init__(self, name='Save', **kwargs):
        super().__init__(name, **kwargs)
        self.out = mp.SimpleQueue()

    def process(self, data, **kwargs):
        self.debug('re data', data)
        self.out.put(data)

    def get_state_and_close(self):
        res = []
        while not self.out.empty():
            res.append(self.out.get())
        self.out.close() # this is important to avoid hanging scripts / tests
        # all mp.queues should always be closed
        return res

@registry.nodes.decorator    
class Quadratic(Node):
    ports_in = Ports_simple()
    ports_out = Ports_simple()

    def process(self, data, **kwargs):
        return self.ret(data=data**2)

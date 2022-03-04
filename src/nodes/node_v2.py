
from enum import Enum


class Location(Enum):
    SAME = 1
    THREAD = 2
    PROCESS = 3
    # SOCKET = 4

class Interface ():
    # === Information Stuff =================

    ports_in = []
    ports_out = []

    category = "Default"
    description = ""

    example_init = {}


    # === Basic Stuff =================
    def __init__(self, name, compute_on=Location.SAME):

        self.name = name
        
        self.inputs = []
        self.outputs = []

        self.clock = None
        if len(self.ports_in) == 0:
            self.clock = (self, 0)

    def __repr__(self):
        pass

    def __str__(self):
        pass

    def __log(self, msg, level):
        pass


    # === Subclass Validation Stuff =================
    def __init_subclass__(self):
        """
        Check if a new class instance is valid, ie if ports are correct, info is existing etc
        """
        pass


    # === Seriallization Stuff =================
    def copy(self):
        pass

    def to_json(self):
        pass

    def from_json(self):
        pass

    def save(self):
        pass

    def load(self):
        pass


    # === Connection Stuff =================
    # TODO: how to initalize connections?
    def add_input(self):
        pass

    def remove_input(self):
        pass

    def __add_output(self):
        pass

    def __remove_output(self):
        pass

    def connect_inputs(self):
        pass


    # === Start/Stop Stuff =================
    def start(self, deep=True):
        pass

    def stop(self, depp=True):
        pass


    # === Data Stuff =================
    def __emit_data(self):
        """
        Called in computation process, ie self.process
        Emits data to childs, ie child.receive_data
        """
        pass

    def __emit_draw(self):
        """
        Called in computation process, ie self.process
        Emits data to draw process, ie draw_inits update fn
        """
        pass

    def receive_data(self):
        pass


    # === Connection Discovery Stuff =================
    def discover_childs(self, deep=True):
        pass

    def discover_parents(self, deep=True):
        pass

    def discover_full(self):
        pass


    # === Drawing Graph Stuff =================
    def dot_graph_childs(self):
        pass

    def dot_graph_parents(self):
        pass

    def dot_graph_full(self):
        pass
    

    # === Performance Stuff =================
    def timeit(self):
        pass


    # === Node Specific Stuff =================
    # (Computation, Render)
    # TODO: figure out how to enable communication between computation and draw processes...
    def process(self):
        pass

    def init_draw(self):
        
        def update():
            pass

        return update

    def init_draw_mpl(self):
        """
        Similar to init_draw, but specific to matplotlib animations
        Should be either or, not sure how to check that...
        """
        pass

import collections
from functools import partial

import json
import importlib
import numpy as np
import queue

from graphviz import Digraph
from PIL import Image
from io import BytesIO

timing_active = False


def activate_timing():
    """
    Tells the Node class to attach a timer to every single node as output
    """
    global timing_active
    timing_active = True


class Node():
    """
    Live system module, with (potentially) inputs and outputs.
    
    Input/Output data should always be 2D numpy arrays with the first
    dimension being samples and the second being dimensions.
    
    To create a new module, override at least addData. You can also
    override add_output, if specific actions are required when adding
    a new output class, and set_input, which is called when this class
    is connected to a new input (this should be done only once).
    
    start_processing() and stop_processing() only need to be overridden
    if your class actually does any parallel processing.

    Class names should always be the same as the python file they're in. 
    Important for saving and loading.
    """

    has_inputs = True
    has_outputs = True
    input_classes = []
    output_classes = []
    frame_callbacks = []

    should_draw = False
    _draw_updates = []
    _draw_data = []


    def __init__(self, name = "Node", dont_time = False, **kwargs):
        """
        Initializes internal state.
        Should not be needed to overwrite, all custom parameters of the child node are stored in self._setup
        """
        self.input_is_set = False
        self.timing_receiver = None
        self.have_timer = False
        self.dont_time = dont_time

        # TODO: not sure how much I like this design. For usage doen'st make a difference, but writing nodes is kinda annoying... no clear acces, no proper default values ...
        self._set_setup(name, **kwargs)

    def _set_setup(self, name, **kwargs):
        """
        Set the Nodes setup settings.
        Primarily used for serialization from json files.
        No need to overwrite.
        """
        self.name = name
        self._setup = kwargs

    def _get_setup(self):
        """
        Get the Nodes setup settings.
        Primarily used for serialization from json files.
        No need to overwrite.
        """
        return self.name, self._setup

    def __call__(self, input_classes):
        """
        Just calls through to set_inputs) and returns self
        for easy chaining.
        """
        self.set_inputs(input_classes)
        return self

    # Called in interactive mode
    # def __repr__(self):
    #     return "Test()"

    # Called on print
    def __str__(self):
        return f"{self.name} [{self.__class__.__name__}]"

    
    def get_timing_info(self):
        """
        Get the timing info for this class and all children, as an ordered dict
        with the hierarchical name and timing sequence.
        
        Note that this will result in some nodes appearing multiple times (if they
        appear in multiple paths from start to end.
        """
        if self.timing_receiver is None:
            return collections.OrderedDict([])
        
        timing_data = collections.OrderedDict([])
        timing_data[self.name] = self.timing_receiver.get_data()
        for output_class in self.output_classes:
            child_timing_info = output_class.get_timing_info()
            for name, sequence in child_timing_info.items():
                timing_data[self.name + "|" + name] = sequence
        return timing_data

    
    def set_passthrough(self, node_in, node_out):
        """
        Sets this node up to just pass through to a sub-graph. Included since
        it is a reasonably common thing to want to do.
        """
        self.get_inputs = node_in.get_inputs
        self.set_inputs = node_in.set_inputs
        self.add_data = node_in.add_data
        self.start_processing = node_in.start_processing
        self.stop_processing = node_in.stop_processing
        
        self.get_outputs = node_out.get_outputs
        self.add_output = node_out.add_output
    
    def get_inputs(self):
        """
        Gets the list of inputs.
        """
        return self.input_classes
    
    def get_outputs(self):
        """Gets the list of outputs."""
        return self.output_classes
    
    def set_inputs(self, input_classes):
        """
        Register an input class. Calling this multiple times is not allowed.
           
        Ideally this should not require overriding ever.
        """
        if not self.has_inputs:
            raise(ValueError("Module does not have inputs."))
        if self.input_is_set:
            raise(ValueError("Module input already set."))
        if not isinstance(input_classes, list):
            input_classes = [input_classes]
            
        for inputId, inputClass in enumerate(input_classes):
            inputClass.add_output(self, inputId)
            
        self.input_classes = input_classes
        self.input_is_set = True
        
    def add_output(self, new_output, data_id = None):
        """
        Adds a new class that this class will output data to. Used
        internally by __call__ / set_inputs to register outputs.

        data_id, if provided, is passed back to the output callback as
        a parameter so that classes can keep multiple inputs apart easily.
           
        In the base case, this also accepts arbitrary functions, which
        will be added as frame callbacks but NOT to the list of classes.
        """
        global timing_active
        if timing_active and (not self.have_timer) and (not self.dont_time):
            self.have_timer = True
            
            # n.b.: This is a circular import of sorts
            from . import Receiver
            self.timing_receiver = Receiver.Receiver(name=self.name + ".Timing",
                                                     perform_timing=True, dont_time=True)(self)
                
        if not self.has_outputs:
            raise(ValueError("Module does not have outputs."))
        
        if isinstance(new_output, Node):
            self.output_classes.append(new_output)
            new_frame_callback_plain = new_output.add_data
        else:
            new_frame_callback_plain = new_output
        
        if data_id is not None:
            new_frame_callback = partial(new_frame_callback_plain, data_id=data_id)
        else:
            new_frame_callback = new_frame_callback_plain
            
        self.frame_callbacks.append(new_frame_callback)
    
    def output_data(self, data_frame):
        """
        Send one frame of data. It should not generally be
        necessary to override this function.
        """
        for frame_callback in self.frame_callbacks:
            frame_callback(data_frame)

        # print(self.should_draw)
        if self.should_draw:
            # print(self._draw_data)
            self._draw_data.extend(data_frame)
    
    def add_data(self, data_frame, data_id=0):
        """
        Add a single frame of data, process it and call callbacks.
        
        Input/Output data should always be 2D numpy arrays with the first
        dimension being samples and the second being dimensions.
        """
        self.output_data(data_frame)  # No-Op
        
    def start_processing(self, recurse=True):
        """
        Starts any parallel running processes that the module needs.
        Can recurse to outputs. Call on the input node to start
        processing for the entire module tree.
           
        When overriding this function, it is recommended that you
        _first_ start processing locally and _then_ recurse.
        """
        if recurse:
            for output_class in self.output_classes:
                output_class.start_processing()
            
    def stop_processing(self, recurse=True):
        """
        Stops any parallel running processes that the module needs.
        Can recurse to outputs. Call on the input node to stop
        processing for the entire module tree.
           
        When overriding this function, it is recommended that you
        _first_ recurse and _then_ stop processing locally.
        """
        if recurse:
            for output_class in self.output_classes:
                output_class.stop_processing()

    def draw(self, *args, **kwargs):
        # print(self.should_draw)
        if self.should_draw:
            # print(self._draw_data)
            data_frame = np.copy(self._draw_data)
            # self._draw_data = []
            # print(self._draw_updates)
            return self._draw_updates[0](data_frame)
        return []

    def make_dot_graph(self, scale = 0.5):
        processing_list = [self]
        dot = Digraph(format = 'png', strict = True)
        while len(processing_list) != 0:
            node = processing_list.pop()
            dot_add_node(dot, node)
            for node_output in node.output_classes:
                dot_add_node(dot, node_output)
                dot.edge(str(node), str(node_output))
                processing_list.append(node_output)
        img = Image.open(BytesIO(dot.pipe()))
        return img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)

    def save (self, path):
        res = save_add_node(self)
        with open(f"{path}.json", 'w') as f:
            json.dump(res, f, indent=2) 


# TODO: find proper places for these...
def load (path):
    with open(f"{path}.json", 'r') as f:
        node = json.read(f)
        return load_add_node(node) 

def save_add_node (node):
    name, settings = node._get_setup()
    return { \
        "class": node.__class__.__name__,
        "name": name,
        "settings": settings, 
        "childs": [save_add_node(node_output) for node_output in node.output_classes]
        }

def load_add_node(node_setting):
    module = importlib.import_module(node_setting['class'].lower())
    node = getattr(module, node_setting['class'])(name=node_setting['name'], settings=node_setting['settings'])
    node.set_inputs([load_add_node(ns) for ns in node_setting['childs']])
    return node

def dot_add_node(dot, node):
    shape = 'rect'
    if node.has_inputs == False:
        shape = 'invtrapezium'
    if node.has_outputs == False:
        shape = 'trapezium'
    dot.node(str(node), node.name, shape = shape, style = 'rounded')
    

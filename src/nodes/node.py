from ast import Return
import collections
from functools import partial

import json
import importlib
import numpy as np
import queue
from typing import DefaultDict

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
    def __init__(self, name = "Node", has_inputs = True, has_outputs = True, dont_time = False):
        """Initializes internal state."""
        self.input_is_set = False
        self.has_inputs = has_inputs        
        self.has_outputs = has_outputs
        
        self.input_classes = []
        self.output_classes = []
        self.frame_callbacks = DefaultDict(list)
        
        self.name = name
        self.timing_receiver = None
        self.have_timer = False
        self.dont_time = dont_time

    def _get_setup(self):
        """
        Get the Nodes setup settings.
        Primarily used for serialization from json files.
        No need to overwrite.
        """
        return { "name": self.name}

    def __call__(self, input_classes):
        """
        Just calls through to set_inputs) and returns self
        for easy chaining.
        """
        self.set_inputs(input_classes)
        return self

    # Called in interactive mode
    def __repr__(self):
        # consider if there is a nice way of displaying the childs as well...
        return f"{str(self)}\n Settings:{json.dumps(self._get_setup())}"

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
        for output_class in self.get_outputs():
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
        self.receive_data = node_in.receive_data
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
        return [n[0] for n in self.output_classes]

    def get_output_instances(self):
        """Gets the list of outputs."""
        # works because the str representation of each node in a pipline must be unique
        # and therefore always the last output entry for the same class is used by overwriting the previous ones
        return {str(n[0]):n[0] for n in self.output_classes}.values()
    
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
        
    def add_output(self, new_output, data_id=None, data_stream="Data", recv_name='receive_data'):
        """
        Adds a new class that this class will output data to. Used
        internally by __call__ / set_inputs to register outputs.

        data_id, if provided, is passed back to the output callback as
        a parameter so that classes can keep multiple inputs apart easily.
        used if a node has multiple inputs from different nodes, but the same type of stream.

        data_stream, if provided, is used to sign up for a specific of multiple output streams.
        output streams are defined in each node.
        used if a node has multiple inputs from different streams (and possibly different nodes).
           
        In the base case, this also accepts arbitrary functions, which
        will be added as frame callbacks but NOT to the list of classes.
        """
        global timing_active
        if timing_active and (not self.have_timer) and (not self.dont_time):
            self.have_timer = True
            
            # n.b.: This is a circular import of sorts
            from .receiver import Receiver
            self.timing_receiver = Receiver(name=str(self) + ".Timing",
                                                     perform_timing=True, dont_time=True)(self)
                
        if not self.has_outputs:
            raise(ValueError("Module does not have outputs."))
        
        if isinstance(new_output, Node):
            if hasattr(new_output, recv_name):
                self.output_classes.append((new_output, data_id, data_stream, recv_name))
                new_frame_callback_plain = getattr(new_output, recv_name)
            else:
                raise Exception('Unknown receiver function')
        else:
            # TODO: consider if we need this feature (functionst, that are not nodes) in the future...
            # Reason is, that these cannot be serialized and may not obey some of the other assumptions about we can make about nodes
            new_frame_callback_plain = new_output
        
        if data_id is not None:
            new_frame_callback = partial(new_frame_callback_plain, data_id=data_id)
        else:
            new_frame_callback = new_frame_callback_plain
            
        self.frame_callbacks[data_stream].append(new_frame_callback)
    
    def send_data(self, data_frame, data_stream="Data", **kwargs):
    # previously called output_data
        """
        Send one frame of data. It should not generally be
        necessary to override this function.
        """
        for frame_callback in self.frame_callbacks[data_stream]:
            frame_callback(data_frame, data_stream=data_stream, **kwargs)

    
    # TODO: figure out how to do the different data streams in **kwargs, but not needing to pass through everything that was before
    # ie playback might output annotation, but not sure if it makes sense for all subsequent nodes to pass that through if only the last one actually needs it...
    # probably requires some sort of sync? ie if playback is connected to "pipeline" and to "accuracy" -> accuracy gets output from playback and pipeline, but (!) they have different function calls...
    def receive_data(self, data_frame, data_id=None, **kwargs):
    # previously called add_data
        """
        Add a single frame of data, process it and call callbacks.
        
        Input/Output data should always be 2D numpy arrays with the first
        dimension being samples and the second being dimensions.
        """
        self.send_data(data_frame)  # No-Op
        
    def start_processing(self, recurse=True):
        """
        Starts any parallel running processes that the module needs.
        Can recurse to outputs. Call on the input node to start
        processing for the entire module tree.
           
        When overriding this function, it is recommended that you
        _first_ start processing locally and _then_ recurse.
        """
        if recurse:
            for output_class in self.get_outputs():
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
            for output_class in self.get_outputs():
                output_class.stop_processing()


    def make_dot_graph(self, scale = 0.5, name=False):
        dot = Digraph(format = 'png', strict = False)

        # as the str rep need to be unique we can get only the unique instances this way 
        nodes = list({str(n):n for n in self.discover_nodes(self)}.values())

        # First pass: create nodes
        for node in nodes:
            shape = 'rect'
            if node.has_inputs == False:
                shape = 'invtrapezium'
            if node.has_outputs == False:
                shape = 'trapezium'
            disp_name = node.name if name else str(node)
            dot.node(str(node), disp_name, shape = shape, style = 'rounded')
        
        # Second pass: add edges based on output links
        for node in nodes:
            for node_output, _, stream_name, _ in node.output_classes:
                stream_name = 'Data' if stream_name == None else stream_name
                dot.edge(str(node), str(node_output), label=stream_name)

        img = Image.open(BytesIO(dot.pipe()))
        return img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)


    @classmethod
    def discover_nodes(self, node):
        if len(node.output_classes) > 0:
            childs = [n.discover_nodes(n) for n in node.get_outputs()]
            return [node] + list(np.concatenate(childs))
        return [node]

    def save (self, path):
        nodes = self.discover_nodes(self)
        
        # TODO: fix this, as we now can have two inputs with different streams :D
        # node_names = list(map(str, nodes))
        # node_names_unique, counts = np.unique(node_names, return_counts=True)
        # if  len(node_names) != len(node_names_unique): # assume the str(n) is unique in a pipeline! 
        #     raise Exception(f'Cannot save as there are nodes with the same string representation, change the name of these nodes {json.dumps(list(node_names_unique[counts > 1]))}')

        nodes = {str(n): { \
                "class": n.__class__.__name__, \
                "settings": n._get_setup(),  \
                "childs": [(str(node_output), output_id, data_stream, recv_name) for node_output, output_id, data_stream, recv_name in n.output_classes if isinstance(node_output, Node)] \
            } for n in nodes}

        with open(path, 'w') as f:
            json.dump({'start': str(self), 'nodes': nodes}, f, indent=2, cls=NumpyEncoder) 

    @classmethod
    def load (self, path):
        with open(path, 'r') as f:
            nodes_settings = json.load(f)
            start_node, nodes_settings = nodes_settings.get('start'), nodes_settings.get('nodes')
            
            nodes = {}
            # instantiate all nodes
            for name, ns in nodes_settings.items():
                # HACK! TODO: fix this proper
                module = importlib.import_module(f"src.nodes.{ns['class'].lower()}")
                nodes[name] = (getattr(module, ns['class'])(**ns['settings']))

            # connect all inputs and outputs 
            # cannot be done earlier, as order of instantiation is important, but not maintained during saving
            for name, ns in nodes_settings.items():
                for ch_name, ch_id, ch_stream, ch_fn in ns['childs']:
                    nodes[name].add_output(nodes[ch_name], data_id=ch_id, data_stream=ch_stream, recv_name=ch_fn)

            return nodes[start_node]


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)
        

# Node

<!-- Role  -->
Nodes are the core unit of the livenodes framework. 
At their core they receive zero or more inputs and produce zero or more outputs using their `process` method. The nodes are then connected via their input/output `ports` to create an acyclic directed computation graph which can be run in [python](./run.md) or [Smart Studio](http://livenodes.pages.csl.uni-bremen.de/smart-studio/index.html).

## Node Structure

I encourage you to look at existing nodes that do similar stuff to what you want to do when creating a new node.

In that spirit, let's have a look at the subtraction node implemented in the [livenodes core nodes package](http://livenodes.pages.csl.uni-bremen.de/packages/livenodes_core_nodes/modules/livenodes_basic_nodes.html#module-livenodes_basic_nodes.math_subtract).

```
class Ports_in(NamedTuple):
    data_1: Port_np_compatible = Port_np_compatible("Data 1")
    data_2: Port_np_compatible = Port_np_compatible("Data 2")

class Math_subtract(Node):
    """ Subtracts Two Numpy Compatible Streams
    
    Takes two streams and subtracts the second from the first 
    using numpys subtract method. 
    
    The data must not be in any specific shape.
    E.g. it does not have to follow the (batch, time, channel) norm.
    """

    # IO Ports
    ports_in = Ports_in()
    ports_out = Ports_np()

    # Meta information
    category = "Transform"
    description = ""

    example_init = {'name': 'Subtract'}

    # Sync Mechanism
    def _should_process(self, data_1=None, data_2=None):
        return data_1 is not None \
            and data_2 is not None

    # Processing Function
    def process(self, data_1, data_2, **kwargs):
        # we assume they have equal sizes or are broadcastable
        return self.ret(data_np=np.subtract(data_1, data_2))

```

It subclasses the `Node` Class and declares the input and output ports. 
Note, that the latter is a class attribute and, therefore, easily accessed in most type hinters, when creating graphs [later on](#Connecting-Nodes-to-a-Graph).

```
class Math_subtract(Node):

    # IO Ports
    ports_in = Ports_in()
    ports_out = Ports_np()
```

It declares two input [Ports](./ports.md), which are of type `Port_np_compatible` and accept anything, that can be cast to a numpy array. The GUI names will be "Data 1" and "Data 2" (passed parameters). In code the port names will be `data_1` and `data_2` as declared in the tuple names.

Important: Values for these ports will be passed as keyword arguments to your `process` and `_should_process` methods, so renaming should be done with care.


```
    # Meta information
    category = "Transform"
    description = ""

    example_init = {'name': 'Subtract'}
```

The meta information of category, description and example initial values are important for Smart Studio and Package managers to group or initialise your nodes. `Example init` will be used as suggestions and type inference for node instantiation values that have no defaults. More information: TODO.


```
    # Processing Function
    def process(self, data_1, data_2, **kwargs):
        # we assume they have equal sizes or are broadcastable
        return self.ret(data_np=np.subtract(data_1, data_2))
```

The heart of your node is the `process` method. In this case it takes two data points and returns the subtraced values. Nothing more, nothing less. 

Important: as noted above the names `data_1` and `data_2` are not random, but all data through the above declared input ports are passed with these keywords. Meaning, that if you rename the first parameter to `data` without updating the ports declaration, `data` will always be `None`.

You might have noticed that the results are not returned directly, but wrapped in a `self.ret` call, where they are assigned to the `data_np` parameter. This parameter is how Livenodes nows which port to send the result through and coresponds to the output port defined analogus to the input port.

You might need to compute results for different output streams one after the other. In that case you can utilize the `self.ret_accu` (for accumulate) and `self.ret_accumulated` like such:
```
    # Processing Function
    def process(self, data_1, data_2, **kwargs):
        # we assume they have equal sizes or are broadcastable
        self.ret_accu(value=np.subtract(data_1, data_2), port=self.ports_out.data_np)
        return self.ret_accumulated()
```

The Livenodes framework will ensure that only synchronised values are passed to your nodes methods, i.e. that the first to ints are subtracted from each other and not the first from the third (by adding a counter in producer style nodes, [see more]()). However, maybe a stream in your node is optional or you want to eagerly process information as soon as it reaches you. This is where `_should_process` comes in. It will be called on every newly received data value and if it returns true `process` will be called. 

The subtract node, ensures that both values are present before accepting a call to `process`.
```
    # Sync Mechanism
    def _should_process(self, data_1=None, data_2=None):
        return data_1 is not None \
            and data_2 is not None
```

Note: if a stream is optional you can explicitly check if it's connected in your `_should_process` method, like such:

```
    def _should_process(self, data=None, optional_parameter=None):
        return data is not None \
            and (optional_parameter is not None or not self._is_input_connected(self.ports_in.optional_parameter))
```


Note: eager processing (i.e. not waiting for all values) can lead to duplicated processing of the same values. Duplicated processing is often a subtle error and is generally not recommended and messes with the [syncronisation mechanism](./streams.md).


## Node Categories

Most nodes will fall into one *or more* of these categories:
- Producer
- Transformer
- Sink
- Visualization / Interaction

A node has access to all of the associated methods described below and thus can be in multiple categories. E.g. a video playback node (producer) that feeds video data into a graph may also have an pause/play interface (visualization / interaction), if desired. Similarly a GUI text field (visualization) can be used for live annotation (transformer) or data storage (sink) can display it's capacity (visualization). 

However, most of the time the node design can be drastically simplified by spliting this behaviour in multiple nodes. Take the data storage example: the data storage may just send it's capacity through a outwards port and you can then choose the visualization (with a bar diagram for instance) or if this should be further processed. In the video example on the other hand, moving the pause button outside would potentially require an infinite memory buffer, whereas in the video node it just abstains from loading more data. As a general Rule, I would recommend to built what you need and *then* consider factoring out. 

### Producers
*Producer* typically don't take an input and are responsible for producing data, which then will be processed by subsequent nodes. They often either implement the `Producer_async` (typically in memory or io producers, for example the [function input](http://livenodes.pages.csl.uni-bremen.de/packages/livenodes_core_nodes/modules/livenodes_basic_nodes.html#module-livenodes_basic_nodes.in_function)) or `Producer_blocking` (typically sensors that have a blocking interface, for example the [plux hub](http://livenodes.pages.csl.uni-bremen.de/packages/livenodes_plux/modules/livenodes_plux.html#livenodes-plux-in-biosignalsplux-module) implementation) node class. 

TODO: describe interface to be implemented and reference documentation.

### Transformers
*Transformers* typically take inputs do some computation and produce an output. This can be simple subtraction or a deep learning model, or whatever you need. The subtraction example from above falls in this category. This is the most common node form.

### Sinks
*Sinks* typically take values and write them to disk. They most often don't produce any output. A good example is the [Out_data node](http://livenodes.pages.csl.uni-bremen.de/packages/livenodes_core_nodes/modules/livenodes_basic_nodes.html#module-livenodes_basic_nodes.out_data).

TODO: describe interface to be implemented and reference documentation.

### Visualization / Interaction
*Visualization* / *Interaction* these nodes declare a graphical user interface which either expects input to be further processed or visualizes data the node received. This is what makes the livenodes framework especially unique, as every node can have this property. 
Good examples are the [matplotlib](http://livenodes.pages.csl.uni-bremen.de/packages/livenodes_matplotlib/) and [qt](http://livenodes.pages.csl.uni-bremen.de/packages/livenodes_qt/) nodes.

TODO: describe interface to be implemented and reference documentation.



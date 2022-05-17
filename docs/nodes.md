# Node System

The graph/node system is iplemented in the node.py module.

Each node consists of named input and output channels through which data is emited and received in form of messages (/ streams) and handled automatically across processes. 
Two Nodes A and B can be connected by using the ```B.add_input(A)``` and ```B.connect_inputs_to(A)``` methods. Indicating, that whenever a message is emitted in Node A it will be passed to node B and for further processing.

There are different kind of Nodes. Each subtype slightly modifies the default ```Node``` class. 
- Transforming Nodes [link]: 
    - theses nodes take an input, perform a calculation and pass the result further along the graph
    - these are implemented by the ```Node``` class and are the archetipical nodes
    - the main function a custom node implementes are the ```process``` and ```should_process`` methods
    - more details here:
- Feeder Nodes [link]: 
    - theses nodes do not have any inputs, but provide data into the graph/pipeline
    - these are implemented by the ```Sender``` or ```BlockingSender``` class
    - by default they are executed in a separate thread as to not block program execution
    - the main function a custom node implements is the ```_run`` method
- Drawing nodes [link]: 
    - these nodes do not have any outputs and provide drawing instructions to a renderer like matplotlib or qt
    - these are implemented by the ```View``` class
    - the main function a custom node implements is the ```_init_draw``` mehtod along with the ```update``` function it returns



Meta information
--- 
each node needs to provide meta information about the following topics:
- which channels are provided
- which channels are processed (some might be optional, but cannot be declared as such atm)
- name
- description, short description of the 
- a category into which the node should be grouped into



Node design:
----
kiss! keep it simple!
the smaller and more consice a node the better! (yes python has a function call overhead, but this is not as relevant here, as modularity or simplicity (they are complicated as they are))


Data streams
---

see: streams.md



building graphs
---
graphs are built by connecting a nodes inputs to some other nodes outputs by function a or b.
you may also remove connections between two nodes.
This can also be done in the gui (see gui.md)
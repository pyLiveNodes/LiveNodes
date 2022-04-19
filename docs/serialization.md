The serialization system can serialize a graph to json (or yml) and deserialize it from json as well.
It uses a couple of assumptions etc for that (these are partialy subject to change).

A major assumption at the moment is, that the python file must be located in the src/nodes/ folder. and that the class in it must have the same name as the file (capitalization is allowed).
This is subject to change and most likely replaced with a global registry which collects nodes on startup.

Another assumption is, that only connected nodes should be saved. Ie nodes, that are not connected to the node on which serialixation is called cannot be discovered and are therefore not saved.

Each node in the graph should have a unique name + class combination. (this will be required in the future, at the moment this is an assumption). If there are two with the same name + class one of them will be dropped from the saving process.

The saving process works as follows:
- call node.save() on the (initial) node / the node whoose subgraph you want to save. 
- this will discover all connected nodes (this might save parents and there subgraphs as well, this api is bound to change)
- then call to_dict on all available nodes 
- save them in a long list
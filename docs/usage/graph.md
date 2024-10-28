# Graphs

Each node consists of named input and output channels through which data is emited and received in form of messages (/ streams) and handled automatically across threads, processes and hosts. 

## Building a Graph

Two Nodes A and B can be connected by using the ```B.add_input(A)``` method in python or the visual representation in LN-Studio. Indicating, that whenever a message is emitted in Node A it will be passed to node B for further processing.

Note: In earlier versions ```B.connect_inputs_to(A)``` was also possible, but lead to implicit errors on changes, and, therefore, is deprecated.

Note: Of course you can edit the json/yaml representation directly as well.

![Example Graph](graph.png)

The example graph in LN-Studio shows two function [producers](./node.md#node-categories) which input the data they emit each to a separate draw node. Furthermore, their data is subtracted from each other and also plotted.

The same graph can be build with python as follows:

```
```

And as json/yaml:
TODO: update as soon as decision on format is made.

```
```

The example graph displays a couple of properties: 
1. Nodes may have mutliple input and output ports (see [node](./node.md))
2. There may be multiple producers in a graph ([see syncronisation]())
3. [Connections are typed](../advanced/streams.md)

Connections are losely typed. If you try to connect incompatible types in LN-Studio or python you will get an error prohibiting you from doing so. However, the typing is lose, that is to say just because you can connect something does not necessarily mean it does make sense: always consider what you are connecting and check the documentation/code. In short: [Type Classes]() implement a check function and provide example values of their type. If at least one of the emiting ports' examples passes the receving ports' type check they may be connected, expecting either an implict cast or that you checked the documentation. 
This lose behaviour allows us to skip most type casting nodes. For example, a list input may accept both a python list as well as a numpy array with only one axis. The strictness of the type is dictated by the types `check_value` method. You can read more [here](../advanced/streams.md).


## Running a Graph

There are multiple ways to run a graph, either directly in LN-Studio providing you with a GUI and interaction environment out of the box or in any python interpreter without interaction. The former is recomended for interaction experiments, the later for signal processing and parameter tuning, to name a few examples.

Note: for interaction you are not restriced to LN-Studio, every draw node expects a QT canvas that it can initialize its drawing on. Therefore, you can build full fledged applications with QT and Livenodes.

Running a graph in LN-Studio is straight forward, select it in the graph selection screen and hit run. 

![Example Graph](graph.png)

Note: if the graph is not shown, make sure to start LN-Studio from the root folder of your project ([more information](https://livenodes.pages.csl.uni-bremen.de/LN-Studio/)).

Running a graph in Python is also straight forward, assuming you have access to any node in the graph.

```
any_node = build_graph(...)

g = Graph(start_node=any_node)
g.start_all()
g.join_all()
g.stop_all()
```

Note, that if you run a live graph wit Python will need to catch keyboard interrupts and call `stop_all` by yourself. In the case of LN-Studio this is handled automatically.

`start_all` will start all producers in the graph. Subsequently on every new data point the following nodes' process methods are called. `join_all` returns once all producers have emited all their data and all nodes have processed their respective data queues. Finally `stop_all` wraps up any remaining threads, processes etc.

Typically your graph will look something like this. Including a Node to access the computed data for further processing in your python interpreter instance. The following example is taken from EASE, where simple statistics per file are calculated and summarized inside a jupyter notebook.

![EASE Plux Statistics Graph](run_example_graph_ease.png)

The graph is build in python:

```
def build_graph(session, hub):
    read_plux = EASE_read_plux(session, hub=hub, shuffle=False)

    fts = Transform_feature(features=['calc_mean', 'calc_std', 'calc_min', 'calc_max'])
    fts.add_input(read_plux, emit_port=read_plux.ports_out.data, recv_port=fts.ports_in.data)
    fts.add_input(read_plux, emit_port=read_plux.ports_out.channels, recv_port=fts.ports_in.channels)

    estimate_sample = EASE_estimate_sample_rate()
    estimate_sample.add_input(read_plux, emit_port=read_plux.ports_out.time, recv_port=estimate_sample.ports_in.time)

    overview = EASE_build_overview()
    overview.add_input(read_plux, emit_port=read_plux.ports_out.session, recv_port=overview.ports_in.session)
    overview.add_input(read_plux, emit_port=read_plux.ports_out.trial, recv_port=overview.ports_in.trial)
    overview.add_input(read_plux, emit_port=read_plux.ports_out.retro, recv_port=overview.ports_in.retro)
    overview.add_input(fts, emit_port=fts.ports_out.data, recv_port=overview.ports_in.features)
    overview.add_input(fts, emit_port=fts.ports_out.channels, recv_port=overview.ports_in.channels)
    overview.add_input(estimate_sample, emit_port=estimate_sample.ports_out.time, recv_port=overview.ports_in.sample_rate)

    out = Out_python()
    out.add_input(overview, emit_port=overview.ports_out.summary, recv_port=out.ports_in.any)
    
    return out
```
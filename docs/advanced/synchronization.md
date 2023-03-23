# Synchronization / Clock

Livenodes tags data packages with a counter created in the producer node it originally emited from in order to sync different channel routes with one another. 

Consider the EASE example pictured below. Let's assume the producer "EASE Plux" emits data and every milisecond and "Features" calculates one milisecond for each data point. Then the streams arriving at "EASE Overview" are mismatched in call order. I.e the first data package is still processed in "Features" when the first Session information reaches the overview. 

TODO: update this with a more abstract example.
![EASE Plux Statistics Graph](../usage/run_example_graph_ease.png)

The delay in a node might be arbitrary high, as it may be on a different host and run compute heavy tasks. Therefore, it is important to be able to match data belonging together, even if it took different length routes through the graph. This is where the Synchronisation / Clock comes into play. Every producer emits a counter with each package most often named `_ctr`. This is done implicitly if you implement one of the producer interfaces. Every subsequent node has access to this `_ctr` as keyword argument in its `process` method. It may overwrite the passed counter, like the `Transform_window` node does. However, most nodes are independent of the time in the graph and can ignore this parameter just focusing on processing and emitting.

## Discussion / Pitfalls

In the current version of livenodes (v0.9.2) the syncronisation is mostly done in-framework and was intended to relive the user from caring to much of how this works. 
The MultiprocessDataStorage module is responsible for keeping data per channel per ctr until the _should_process returns true and the data for that and previous ctrs is deleted. 

### Multiple Producers

Multiple Producers work out of the box in most cases, however, they are not very intuitive as it is not directly clear why/how packages are merged. Most of the time both producers will start with the counter 0, so these packages are merged. Generally, this is the intended way, but it is never explicitly declared and no guarantee is given, use explicity Sync nodes when you need control on how data is aligned.

### Implicit/Explicit Sync
Currently the sync is implicitly handeld by the Livenodes framework. Every time data is received through a connection the `_should_process` method is called with all so far stored values from the current counter. If it returns true, `process` is called and (!) the stored data from that counter and all below deleted. Again, generally, this is the intended behaviour. However, the `_should_process` often is misunderstood. In future versions the functionality the framework currently handles is likely provided through a method interface and each node will need to explicitly do sync itself.

### Multiple Process Invocations per ctr
Due to the counter being mostly passed for identification a node should not emit through a single connection multiple times per invocation to its' `process` method and expect all data to be saved. Essentially: the receiving node will get two different data points for the same ctr. A good example is the BioKIT train node, which posts out it's trainign status and updates this multiple times through the same channel. If this status is just displayed (e.g. with Print_data) all calls are directly processed, displayed and only the last stays printed.
However, if the receiving node waits for another input, the first call data will be overwritten by the second call. The receiving node doesn't even know there was a previous value. However, it might also be the case, that the second value was already present due to a race condition. In that case the first value will be used and the second never processed. 
In the end, most nodes do not need to emit multiple data points per invocation to their `process` method and should avoid to do so, if possible.

### Time vs Ctr
Packages are syncronised with the assigned counters. If you need to merge/sync from different producers using closness in time, you can use the duration between invocations to your nodes `process` method for sync (as does the Sync_nearest node). Alternatively, lets discuss if it would make sense to tag the packages with the current epoch timestamp, rather than an arbitray counter. -> please open an issue on gitlab/livenodes/livenodes.



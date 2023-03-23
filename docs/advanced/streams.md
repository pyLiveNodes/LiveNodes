# Streams / Connections

Streams are data pipes passing a nodes emiting data to a receving nodes process method. The connections types are determined by the port declarations of the two connected nodes and every connection only connects two nodes. The actual data passing is implemented using `Bridges`, which are responsible for passing data across threads, processes and hosts ([more information]()).

## Port Types

Port clases implement a `check_value` function and provide example values of their type. If at least one of the emiting ports' examples passes the receving ports' type check they may be connected, expecting either an implict cast or that you checked the documentation. 
This lose behaviour allows us to skip most type casting nodes. For example, a list input may accept both a python list as well as a numpy array with only one axis. The strictness of the type is dictated by the types `check_value` method.

Here is the List Port from the [core nodes package](https://gitlab.csl.uni-bremen.de/livenodes/packages/livenodes_core_nodes), which implements a broad list of types. It declares different kinds of lists in its' `example_values`. Lists of strings, lists of floats, and also numpy arrays are allowed, which is also ensured with the `check_value` method. The list type is special in that it supports nesting/compounds. This allows to define types for the lists entries. In this case all examples and the `check_value` from `Port_Any` are allowed. This is especially usefull if you have more specific requirements. For instance you might want to build a Port Type, that only accepts numpy int arrays conforming to the shape (Batch, Time, Channel). More on that in the [Best Practices Section](#best-practices).

```
class Port_List(Port):
    example_values = [
        ["EMG1", "EMG2", "EMG2"],
        [0, 1],
        [0, -1],
        [20, .1, .1],
        np.array([20, 1])
    ]

    compound_type = Port_Any

    @classmethod
    def check_value(cls, value):
        if not (type(value) == list or isinstance(value, np.ndarray)):
            return False, f"Should be list; got {type(value)}, val: {value}."
        if len(value) > 0:
            return cls.compound_type.check_value(value[-1])
        return True, None

```


## Best Practices

Technically every node may declare any type of stream and may send data at any point it wants. However, there are some best practices I would recommend. 

### (Batch, Time, Channel) Format

One of the core ideas is, that the same nodes may be used for offline hyperparameter tuning and interactive online applications. However, intuitively the data would look different: offline data spans multiple sessions and participants while online data is typically from one particpant in one session. 
I would recommend to treat this explicitly, i.e. use the (Batch, Time, Channel) format as much as possible. In the case of offline Data I would recomend to treat each file as batch, while in the online case the batch axis is present but unused. 
TODO: visualize this and consider if this actually makes sense... tbh i'm not sure it does. i.e. offline with batch=file requires window to not use overlapping samples, while in the case of online (with unused batch) window would need to buffer samples...

### Stream vs Event

Some data is constantly changing, while some mostly remains the same. The most common example in biosignals is the recorded data and the channel names of the sensor. Take the PLUX BiosignalsHUB, it will constantly emit new data, but the channel names may only change if you plugin new sensors. For most sensors this never changes during runtime. Nevertheless this is data you want to take into account. For plottinge, channel selection, feature calculation and more it is super useful to know the names of each channel alongside the data in the channel.

Both streams and events have their merit and LiveNodes does not enforce one or the other. That being said mixing both is a difficult task and I would recommend avoiding that where possible. 
Take the data + channel names example. Lets say data is a stream and channel names are event-based. Due to the multi-input nature of Nodes, each data point on a clock tick is passed separately (see [TODO]()).
If a subsequent node now receives data it does not now if a change in channel names will follow or not. It should not wait for the next tick to process, as this introduces a delay, but if it processes data and channel names are passed afterwards it just processed the data incorectly. I.e. assume you disconnected a sensor, which might be handled correctly by the producer node setting that channel to NaN and updating the channel names, but a subsequent the channel select now may have let that NaN pass, as it only is aware of the change after processing the data and assuming no change in channel names would happen. Most of the time nothing tragic happens, but I would recommend to avoid mixing the two.
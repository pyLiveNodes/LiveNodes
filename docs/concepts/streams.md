# Streams

Every node may declare any stream it likes.

Streams are currently based on the strings provided by each node. Similar to the node system, in the future a class and registry might be implemented.

these are the streams currently used in the standard nodes:
- Data: a numpy array of shape (batch/file, time, channel)
Every node working with this stream should always comply to this standard, even if one of the dimensions might just be of size one.

# Inter Process Communication


# Bridges

# Bridge Registry


# Setup before running

1. whole Graph is loaded into main thread and all nodes initialized
2. each node is locked (ie no new connections or setting changes are allowed)
    1. this results in the bridges being resolved (still in the main thread) 
    2. and endpoints being created ie pipe writing and pipe receiving points / queue etc
    <!-- 3. the endpoints are passed back to  -->
3. the nodes and their according endpoints are passed to their according computers: (local / asyncio) threading, processing, ...
4. the nodes receive their input and output endpoints within the computer and establish the rest of their routine to be ready for running (ie the ready call for a node?)



# Alternative IPC setup

## Pipes
Might be worth to think some more about pipes...

Note on design pattern where nodes connect by themselfes and send the endpoints to their specific counterparts via the parent process. 

ie. 
child a: "hey parent could you pass this endpoint to child b"?
parent to child b "i've got this recev endpoint / input from child a for ya"

This not possible with queues, as they cannot be passed between process other than through inheritance.

From the docs: https://docs.python.org/3/library/multiprocessing.html#multiprocessing.connection.Connection.recv_bytes_into

Changed in version 3.3: Connection objects themselves can now be transferred between processes using Connection.send() and Connection.recv().


## Shared Memory
- Might be awesome, but requires knowlegde about the data to be send as well as the required size (?)
- Might lend itself more to bridges than to node-view coms 
(on that note: it might be worth considering the same coms process for node-view as node-node -> allows for visualization of nodes on a different pc -> not sure if that is a good idea tho... pro: vis from another pc, same performance improvements as in bridges; con: no way to drop vis requests if overflowing, lag in interaction from vis to actual node-running code; confusion if at somepoint two uis on different pcs)

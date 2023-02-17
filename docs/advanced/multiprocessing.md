# Multiprocessing

Each node can be executed in either the main process (location.same), a thread in the main process (location.thread) or a subprocess (location.process). Message passing and everything else is handled automatically. 

in the future nodes across machines is considered. for this messages should be passed via websockets etc. but at the moment this is not implemented and no timeframe considered.



notes on new mp:
- each thread no matter where it runs, no matter how many nodes in it, uses an asyncio loop to register task callbacks, which basically scouer a nodes' task queue, allowing mulitple nodes to wait for input
- a node adds tasks its output to anothers task queue if it is done processing (ie emit_data)
- multiprocessing and / or multimachines, then should spin up another process (with it's own asyncio queue) and provide a pridge on how to put items into the next nodes task queue
-> maybe not have nothing running localy at all? -> ie have the queues at least in a thread/process/other computer, thus always having the starting thread non-blocking?
-> nodes would add tasks to the threads queue and the thread would return once all tasks are processed (?)

[x] TODO: define interface for this, as it currently is a little fuzzy
[ ] TODO: the node starting call doesn't work out yet, how to call start in main, but then proceed in thread? -> technically we need to pass the nodes anyway, just call each node on start i guess

<!-- 1) main thread
- call start on any node
    - collect start nodes in graph 
    - start threads/processes/networking devices across all nodes
    - tell all nodes to ready (formerly start_node) (see 2) II)
    - tell all threads/p/n to spin up their asyncio queues and return once all tasks are done
        -> each node registered a finish future/promise when being started
    - return
- call stop on any node (force=bool)
    - tell all threads to (gracefully) stop their asyncio loops
    - return (once all threads returned)

2) in each thread:
- on start: create asyncio loop
- for each node: 
    - add tasks to loop
    - add finish to loop and register with main
    - recurse once a task is done but no termination signal was send -->

// generally this is nice, tho -> as the thread/p/n class can easily be abstracted into a service 
// also then compute_on should become something like: host:process:thread


1) main thread
graph.start
- collect locations across all node
- spin up computers for each location, passing the according nodes (see 2.start)
- release "start-working-lock"
- return

graph.stop
- call stop on each computer (see 2.stop)

2) computer (thread/process/network computer etc):
computer.start_suprocces
- create asyncio loop
- ready all nodes (see 3)
- block until we can aquire the "start_working" lock (alternatively find nicer way to wait for instructions from main thread)
<!-- TOOD: how can we ensure the order of nodes here? -> we do not have to, all nodes should be ready to receive data and naturaly the producers will start the chain -->
- run asyncio loop until all _finished futures are resolved (this will kickoff 3.process)
- return / close computer

computer.stop (force=False)
- join thread (will return once all _finished promises are resolved)

computer.stop (force=True)
- terminate()

3) ready node:
node.ready / formerly start_node
- add recursive await (package/task) queue as task to local asyncio loop
    - once a package was processed add task again if not received "final package" (in this case do not recurse, but resolve _finished promise)
- create _finished future/promise 
- return

node.process (called once the recursive await from 3.ready resolves)
- call own should_process and process
- emit_data -> use bridge to put data into the recv nodes (package/task) queue (see 4)

4) bridge
bridge.put
- depending on emit and recv use different means (hence "bridge"):
    - same thread: normal asyncio.queue
    - different process: 
        - mp.queue + wrapper
        - shared memory
    - different networ pcs: 
        - lsl
        - tcp
        - ...

async bridge.get
-> wrap bridge transporation layer into an async statement


TODO: how to tell if a bridge will not be needed anymore?
a) last_package -> not always clear / unambigous: consider channel_names, which are sent once at the beginning, so that bridge would be closed, but the data one would not.i
-> maybe rather use the last_package idea from a producer to:
b) call close on all bridges once producer is finished sending data. similarly call close on all bridges once all inputs from a node are closed 
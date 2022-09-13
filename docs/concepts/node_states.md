
A graph follows these stats:
- initialized -- init(node)
    - all connected nodes discovered (and loaded)
- started -- start_all()
    - all computers initalized and started
- stopped -- stop_all()
    - all computers stopped and closed
    - all computers cleaned up
    - (all nodes reloaded?)

A computer follows these states:
- initialized -- init(nodes)
    - all locks created and all nodes loaded
- ready -- setup()
    - supbprocess created
    - in sub: all nodes readied
- started -- start()
    - in sub: all nodes started
- stopped -- stop(timeout)
    - in sub: all are given the chance to gracefully stop
    - // needed for multiple interdependent computers to be gracefully shut down
- closed -- close()
    - in sub: all nodes forced to stop
    - subprocess closed

TODO: i think i mixed computer, node and the computer/worker thread here...

A node follows these states:
- initialized -- init()
    - the class is instantiated
- ready -- ready()
    - all bridges(/connections) are established
    - all listeners are registered to the event loop
    - (> should call _onready() ?)
- started -- start()
    - > calls _onstart()
    - now produces/transforms data
a) finished -- implicit
    - all input bridges are closed, resulting in all output bridges being closed
    - no production / transformation of data going on
    - node will call _onstop by itself 
b) stopped -- stop()
    - > calls _onstop()
<!-- - close -- close()
    - (force) de-registers all listeners
    - (force) closes all bridges -->

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

# Livenodes

Livenodes are small units of computation for digital signal processing in python. They are connected multiple synced channels to create complex graphs for real-time applications. Each node may provide a GUI or Graph for live interaction and visualization.

//SMART-Studio is a GUI Application to create, run and debug these graphs based on QT5.

Any contribution is welcome! These projects take more time, than I can muster, so feel free to create issues for everything that you think might work better and feel free to create a MR for them as well!

Have fun and good coding!

Yale


To disable assertion checks for types etc use
```
PYTHONOPTIMIZE=1 smart_studio
```


# Known Bugs:

## nodes not computing due to multiprocessing issues
Scenario:
1. node A runs in a thread
2. node B runs on another thread, but with location = Same
3. A calls emit_data in its own process()
4. this triggers a call of B.receive_data, but in the context of As thread
=> if B also waits for input from a node C, the data will be processed on different threads and will not be syncronised

### Circumvent / Hack:
Set node B to location = 2 or 3.
This works, because the state manager opens up a multiprocessing queue and therefore can receive data from multiple threads/processes.
(Also then B triggers not via direct call, but when the queue has data.)

### Proper solution:
The proper solution would be to implement "connections", ie passing data and triggering "process" functions is then handled by a conneciotn class, that differs based on which things are connected.

ie if the connection is same->same => use class SameSame which triggers directly (or with asyncio for non-blocking behaviour), if the conneciton is process->same => use class ProcessSame which handles this case accordingly.

This then would also allow for optimized connections to replace default ones. ie process->process might also be solved with shared memorey, rather than a multiprocessing queue.

## multiple smaller ones

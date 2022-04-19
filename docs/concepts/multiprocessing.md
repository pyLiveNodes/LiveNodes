# Multiprocessing

Each node can be executed in either the main process (location.same), a thread in the main process (location.thread) or a subprocess (location.process). Message passing and everything else is handled automatically. 

in the future nodes across machines is considered. for this messages should be passed via websockets etc. but at the moment this is not implemented and no timeframe considered.
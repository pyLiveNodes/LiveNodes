Feeder nodes and sync nodes provide a clock wich acts as a takt for their whole subgraph.

This allows subgraphs to be synced on the same clock.
ie 
consider a -> b, b-> c and a -> c
with this clock concept, c knows which of the received messages of a and b belong to the same time step and may choose to wait before processing. it may also consider to already emit one channel and wait with another until all information is avaliable. 

It might be of interest to already send some infortmation as then possible expensive subghraph parts can execute as fast as possible.
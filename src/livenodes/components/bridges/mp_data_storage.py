import asyncio
from livenodes.components.node_logger import Logger

from livenodes.components.connection import Connection

from livenodes import get_registry

import logging
logger = logging.getLogger('livenodes')

# TODO: this should be part of Node class or at least a mixin?
class Multiprocessing_Data_Storage(Logger):
    # enpoints should be dicts with con.key: bridge
    def __init__(self, input_endpoints, output_endpoints) -> None:
        super().__init__()
        
        self.in_bridges = input_endpoints
        self.out_bridges = output_endpoints

        for bl in self.out_bridges.values():
            for b in bl:
                b.ready_send()

        for b in self.in_bridges.values():
            b.ready_recv()
        
    @staticmethod
    def resolve_bridge(connection: Connection):
        emit_loc = connection._emit_node.compute_on
        recv_loc = connection._recv_node.compute_on

        # # print('----')
        # # print(connection)
        # # print('Bridging', emit_loc, recv_loc)
        # # print('Bridging', parse_location(emit_loc), parse_location(recv_loc))

        possible_bridges_pair = []
        for bridge in get_registry().bridges.values():
            can_handle, cost = bridge.can_handle(_from=emit_loc, _to=recv_loc)
            if can_handle:
                possible_bridges_pair.append((cost, bridge))

        if len(possible_bridges_pair) == 0:
            raise ValueError('No known bridge for connection', connection)

        possible_bridges = list(zip(*list(sorted(possible_bridges_pair, key=lambda t:t[0]))))[1]
        logger.debug(f'Possible Bridges in order: {possible_bridges}')
        logger.info(f'Using Bridge: {possible_bridges[0]}')
        
        bridge = possible_bridges[0](_from=emit_loc, _to=recv_loc)
        endpoint_send, endpoint_receive = bridge, bridge
        return endpoint_send, endpoint_receive

    # _to thread
    def all_closed(self):
        return all([b.closed() for b in self.in_bridges])

    # _to thread
    async def on_all_closed(self):
        await asyncio.gather(*[b.onclose() for b in self.in_bridges.values()])
        self.info('All bridges empty and closed')

    # TODO: may be removed?
    def empty(self):
        return all([q.empty() for q in self.in_bridges.values()])

    # _to thread
    def get(self, ctr):
        res = {}
        # update current state, based on own clock
        for key, queue in self.in_bridges.items():
            # discard everything, that was before our own current clock
            found_value, cur_value = queue.get(ctr)

            if found_value:
                # TODO: instead of this key transformation/tolower consider actually using classes for data types... (allows for gui names alongside dev names and not converting between the two)
                res[key] = cur_value
        return res 
    
    # _to thread
    def discard_before(self, ctr):
        for bridge in self.in_bridges.values():
            bridge.discard_before(ctr) 

    # _from thread
    def put(self, output_channel, ctr, data):
        # # print('data storage putting value', connection._recv_port.key, type(self.bridges[connection._recv_port.key]))
        # we are the emitting part :D
        # for b in self.out_bridges[connection._emit_port.key]:
        for b in self.out_bridges[output_channel]:
            b.put(ctr, data)

    # _from thread
    def close_bridges(self):
        # close all bridges we put data into
        for bridge_list in self.out_bridges.values():
            for bridge in bridge_list:
                bridge.close()

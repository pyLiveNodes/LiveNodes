import sys
import threading, queue
import datetime
import os
import time

import numpy as np
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher

# User modules

import asyncio

CHANNELS = ["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z", "MAG_X", "MAG_Y", "MAG_Z","TEMP", "IO", "A1", "A2", "C", "Q1", "Q2", "Q3", "Q4", "PITCH", "YAW", "ROLL", "HEAD"]
FACTORS  = np.array([1/x for x in [8, 8, 8, 2, 2, 2, 2, 2, 2, 1, 1, 1, 4095, 4095, 1, 1, 1,  1, 180, 180, 180, 180]])

class RIoT():
    channels = ["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z", "MAG_X", "MAG_Y", "MAG_Z","TEMP", "IO", "A1", "A2", "C", "Q1", "Q2", "Q3", "Q4", "PITCH", "YAW", "ROLL", "HEAD"]
    factors  = np.array([1/x for x in [8, 8, 8, 2, 2, 2, 2, 2, 2, 1, 1, 1, 4095, 4095, 1, 1, 1,  1, 180, 180, 180, 180]])

    def __init__(self, id, dispatcher):
        self.dispatcher = dispatcher
        self.dispatcher.map(f"/{id}/raw", self.onRawFrame)
        self.id = id

    # Callbacks override
    def onRawFrame(self, addr, *data):
        print(np.array(list(data))*self.factors)
        # self.data = (np.array(list(data))*self.factors)

async def collect ():       
    disp = Dispatcher()
    keep = ["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z", "MAG_X", "MAG_Y", "MAG_Z", "Q1", "Q2", "Q3", "Q4", "PITCH", "YAW", "ROLL", "HEAD"]
    device = RIoT(id=0, dispatcher=disp)
    # disp.map("/0/raw", filter_handler)
    listen_ip='192.168.1.101'
    listen_port=8888
    server = AsyncIOOSCUDPServer((listen_ip, listen_port), disp, asyncio.get_event_loop())
    transport, protocol = await server.create_serve_endpoint()

    ctr = 2000
    while (ctr > 0):
        ctr -= 1
        await asyncio.sleep(0)

    transport.close()

# asyncio.run(collect())


# from pythonosc.osc_server import AsyncIOOSCUDPServer
# from pythonosc.dispatcher import Dispatcher
# import asyncio


# def filter_handler(address, *args):
#     print(f"{address}: {args}")


# dispatcher = Dispatcher()
# dispatcher.map("/0/raw", filter_handler)

# listen_ip='192.168.1.101'
# listen_port=8888


# async def loop():
#     """Example main loop that only runs for 10 iterations before finishing"""
#     for i in range(1000):
#         print(f"Loop {i}")
#         await asyncio.sleep(1)


# async def init_main():
#     server = AsyncIOOSCUDPServer((listen_ip, listen_port), dispatcher, asyncio.get_event_loop())
#     transport, protocol = await server.create_serve_endpoint()  # Create datagram endpoint and start serving

#     await loop()  # Enter main loop of program

#     transport.close()  # Clean up serve endpoint


# asyncio.run(init_main())


# class pluxModule:
#     endingFlag = False
#     devices = []
#     frameCounter = 0
#     buffer = queue.Queue()

#     def __init__ (self, device_ids, listen_ip='192.168.1.100', listen_port=8888):
#         self.device_ids = device_ids
#         self.listen_ip = listen_ip
#         self.listen_port = listen_port

#         self.dispatcher = dispatcher.Dispatcher()

#         # keep = None
#         # keep = ["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z", "MAG_X", "MAG_Y", "MAG_Z"]
#         keep = ["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z", "MAG_X", "MAG_Y", "MAG_Z", "Q1", "Q2", "Q3", "Q4", "PITCH", "YAW", "ROLL", "HEAD"]

#         self.devices = [RIoT(id=i, dispatcher=self.dispatcher, keep=keep) for i in self.device_ids]

#     def stop(self):
#         self.endingFlag = True
#         return

#     async def loop (self):
#         self.server = osc_server.AsyncIOOSCUDPServer((self.listen_ip, self.listen_port), self.dispatcher, asyncio.get_event_loop())
#         self.transport, self.protocol = await self.server.create_serve_endpoint()
#         await self.loop_helper()
#         self.transport.close()

#     async def collect_frame_wait_on_all(self, num_sensors):
#         # waits until each sensor added a signal, always keeping the last data. Yes, this might skip frames and is not ideal, feel free to improve on :-)
#         # probably easiest solution for plotting, since main feature in cls is mean, eager input is probably better for ml...
#         res = [[]] * num_sensors
#         contr =  np.zeros(num_sensors)
#         # i = 0 # TODO: maybe add timeout error later on (would need to be based on cpu clock or time module)
#         while (True):
#             for i, pluxDevice in enumerate(self.devices):
#                 tmp = pluxDevice.read_data()
#                 if tmp != []:
#                     res[i] = tmp
#                     contr[i] = 1
#                     if np.sum(contr) == num_sensors:
#                         return list(np.concatenate(res))
#             await asyncio.sleep(0)
#             # i += 1
#             # if i > 1000:
#             #     raise Exception('Timeout')

#     async def loop_helper(self):
#         n_sensors = len(self.devices)
#         while (True):
#             frameData = await self.collect_frame_wait_on_all(n_sensors)
#             self.buffer.put([frameData])
#             self.frameCounter += 1
#             await asyncio.sleep(0)

#             if self.endingFlag:
#                 break

#     def get_channel_names(self):
#         return list(np.concatenate([[f'{i}_{channel}' for channel in dev.channels] for i, dev in enumerate(self.devices)]))

#     def start(self):
#         asyncio.run(self.loop())


"""Small example OSC server adapted from https://pypi.org/project/python-osc/
    
    This program listens to addresses with the address /<id>/raw where id is an integer
    If the connection is successful, incoming data will be printed in the console
    
    Default aguments assume the standard network configuration of the R-IoT module out-of-the-box. If these have been change, please alter the arguments accordingly
    """
import argparse
import math

from pythonosc.osc_server import AsyncIOOSCUDPServer, ThreadingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
import asyncio

labels = ["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z", "MAG_X", "MAG_Y", "MAG_Z","TEMP", "IO", "A1", "A2", "C", "Q1", "Q2", "Q3", "Q4", "PITCH", "YAW", "ROLL", "HEAD"]

## Data arrives to this function as a sinlge tuple argument
## This contains 22 floats values
def riot_handler(addr, *data):
    print(addr)
    print(data)
    print('======')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip",
        default="192.168.1.101", help="The ip to listen on")
    parser.add_argument("--port",
        type=int, default=8888, help="The port to listen on")
    args = parser.parse_args()
            
    dispatcher = Dispatcher()
    dispatcher.map("/*/raw", riot_handler)
                
    server = ThreadingOSCUDPServer((args.ip, args.port), dispatcher)
    print("Serving on {}".format(server.server_address))
    server.serve_forever()

    # async def loop():
    #     """Example main loop that only runs for 10 iterations before finishing"""
    #     for i in range(10):
    #         print(f"Loop {i}")
    #         await asyncio.sleep(1)


    # async def init_main():
    #     server = AsyncIOOSCUDPServer((args.ip, args.port), dispatcher, asyncio.get_event_loop())
    #     transport, protocol = await server.create_serve_endpoint()  # Create datagram endpoint and start serving

    #     await loop()  # Enter main loop of program

    #     transport.close()  # Clean up serve endpoint


    # asyncio.run(init_main())
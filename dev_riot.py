
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
from collections import defaultdict
import time

labels = ["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z", "MAG_X", "MAG_Y", "MAG_Z","TEMP", "IO", "A1", "A2", "C", "Q1", "Q2", "Q3", "Q4", "PITCH", "YAW", "ROLL", "HEAD"]

## Data arrives to this function as a sinlge tuple argument
## This contains 22 floats values
ctrs = defaultdict(int)
times = defaultdict(int)
def riot_handler(addr, *data):
    global ctrs, times
    ctrs[addr] += 1
    if times[addr] == 0:
        times[addr] = time.time()

    every = 100
    if ctrs[addr] % every == 0:
        t2 = time.time()
        t_diff = t2 - times[addr]
        times[addr] = t2
        fps = every / t_diff
        print(f"{addr}; Received {ctrs[addr]} frames in {t_diff:.2f} seconds. This equals {fps:.2f}Hz.")

    # print(addr, ctrs[addr])
    # print(data)
    # print('======')

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
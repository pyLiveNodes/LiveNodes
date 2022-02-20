import time
import numpy as np
from multiprocessing import Process
import threading
from .node import Node
import glob, random
import pandas as pd
import random

from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher
import asyncio


class In_riot(Node):
    channels = ["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z", "MAG_X", "MAG_Y", "MAG_Z","TEMP", "IO", "A1", "A2", "C", "Q1", "Q2", "Q3", "Q4", "PITCH", "YAW", "ROLL", "HEAD"]

    def __init__(self, id=0, name="RIoT", listen_ip='192.168.1.101', listen_port=8888, dont_time=False):
        super().__init__(name, has_inputs=False, dont_time=dont_time)
        self.feeder_process = None

        self.id = id
        self.listen_ip = listen_ip
        self.listen_port = listen_port

        # self.feeder_process = None
        self._stop_event = threading.Event()
    
    def _get_setup(self):
        return {\
            "id": self.id,
            "listen_ip": self.listen_ip,
            "listen_port": self.listen_port,
        }

    @staticmethod
    def info():
        return {
            "class": "In_riot",
            "file": "In_riot.py",
            "in": [],
            "out": ["Data", "Channel Names"],
            "init": {
                "name": "Name"
            },
            "category": "Base"
        }
    
    @property
    def in_map(self):
        return {}

    async def collect(self):
        factors = np.array([1/x for x in [8, 8, 8, 2, 2, 2, 2, 2, 2, 1, 1, 1, 4095, 4095, 1, 1, 1,  1, 180, 180, 180, 180]])

        def onRawFrame (addr, *data):
            # nonlocal factors
            # print(addr, data)
            # print(np.array(data).shape)
            self.send_data([np.array(list(data))*factors])
            # self.send_data([data])

        disp = Dispatcher()
        disp.map(f"/{self.id}/raw", onRawFrame)
        server = AsyncIOOSCUDPServer((self.listen_ip, self.listen_port), disp, asyncio.get_event_loop())
        transport, protocol = await server.create_serve_endpoint()

        while (not self._stop_event.is_set()):
            await asyncio.sleep(0)

        transport.close()

    def sender_process(self):
        """
        Streams the data and calls frame callbacks for each frame.
        """

        self.send_data(self.channels, data_stream="Channel Names")

        asyncio.run(self.collect())

    
    def start_processing(self, recurse=True):
        """
        Starts the streaming process.
        """
        if self.feeder_process is None:
            self.feeder_process = threading.Thread(target=self.sender_process)
            # self.feeder_process = Process(target=self.sender_process)
            # self.feeder_process.daemon = True
            self.feeder_process.start()
        super().start_processing(recurse)
        
    def stop_processing(self, recurse=True):
        """
        Stops the streaming process.
        """
        if self.feeder_process is not None:
            # set stop and wait for it to go through
            self._stop_event.set()
            self.feeder_process.join()
            # self.feeder_process.terminate()
        self.feeder_process = None
        # our own close is called first, as we don't want to send data to a closed output
        super().stop_processing(recurse)

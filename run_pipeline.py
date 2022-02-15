from matplotlib import animation
from src.nodes.blit import BlitManager

from src.nodes.node import Node, activate_timing

import numpy as np
import matplotlib.pyplot as plt
import matplotlib

import time
import threading
from multiprocessing import Process

import math

TIME = False

print('=== Load Pipeline ====')
if TIME: activate_timing()
pipeline = Node.load('pipelines/process_live.json')


print('=== Start pipeline ====')

# Threading example
# worker = threading.Thread(target = pipeline.start_processing)
# worker.daemon = True
# worker.start()

worker = Process(target = pipeline.start_processing)
worker.start()
worker.join()

if TIME:
    # see https://gitlab.csl.uni-bremen.de/bioguitar/livenodes/-/blob/master/notebooks/NewInterfaceTest.ipynb
    # for an example how to plot 
    print(pipeline.get_timing_info())

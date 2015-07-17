"""

  NAME
    benchmark.py - a python implementation of the MCAPI standard benchmark

  DESCRIPTION
    This benchmark implements a simple performance test of the MCAPI interface
    by measuring how many tell position (TP) it can execute in one second. This
    is similar to the bench32.exe/bench64.exe compiled utilities and may be 
    used to directly compare python performance to native binaries.

    To run:
      python benchmark.py

  RELEASE HISTORY
    Copyright (c) 2015 by Precision Micro Control Corp. All rights reserved.

    $Id: benchmark.py 921 2015-06-23 18:16:19Z brian $

    Version 4.4.1		23-Jun-15		Programmer: R. Brian Gaynor
      - First release

"""
from mcapi import *
import time

print("Test interface performance using Tell Position (TP) loop. The results")
print("are given in the number of Tell Position commands executed per second.")

""" create a controller object and open a controller """
controller = Mcapi()

""" ASCII mode test """
controller.Open(0, MC_OPEN_ASCII)
limit = 5000
print("ASCII Mode TP Test Start")
start = time.time()
for i in range(0, limit):
	controller.GetPositionEx(1)
stop = time.time()
total = stop - start
print("Elapsed time: {0:.3f} sec, TP/second: {1:.2f}".format(total, limit / total))
controller.Close()

""" Binary mode test """
controller.Open(0, MC_OPEN_BINARY)
limit = 50000
print("Binary Mode TP Test Start")
start = time.time()
for i in range(0, limit):
	controller.GetPositionEx(1)
stop = time.time()
total = stop - start
print("Elapsed time: {0:.3f} sec, TP/second: {1:.2f}".format(total, limit / total))
controller.Close()

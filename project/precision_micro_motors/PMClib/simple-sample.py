"""

  NAME
    simple-sample.py - a simple command line sample of MCAPI python usage

  DESCRIPTION
    This simple python sample uses the MCAPI python binding to open a motion
    controller, determine how many axes are supported, and dump axis position
    info to the console. This uses the controller at ID #0 (should be the 
    default) just to keep things simple (really simple).

    To run:
      python simple-sample.py

  RELEASE HISTORY
    Copyright (c) 2015 by Precision Micro Control Corp. All rights reserved.

    $Id: simple-sample.py 921 2015-06-23 18:16:19Z brian $

    Version 4.4.1		23-Jun-15		Programmer: R. Brian Gaynor
      - First release

"""
from mcapi import *

# create a controllerobject an open the controller at ID #0
ctlr = Mcapi()
ctlr.Open(0, MC_OPEN_BINARY)

# use GetConfigurationEX() to determine how many axes we have
param = MCPARAMEX()
ctlr.GetConfigurationEx(param)

# query all axes for position (position is defined as a ctype so that it is mutable)
for axis in range(1, param.NumberAxes + 1):
	print("Axis", axis, "is at position", ctlr.GetPositionEx(axis))

# close the handle
ctlr.Close()

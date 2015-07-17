"""

  NAME
	init.py - handy script to set up Motion Control API for interactive use

  DESCRIPTION
    This small script loads the MCAPI libraries (base API and motion dialogs), opens
    a controller, and gets config data for the controller and a selected access. This 
    makes it easier to jump into using the MCAPI interactively. To run (and stay in 
    the interpreter):

    python -i init.py

    By default the controller at ID 0 will be opened and the axis configuration for 
    axis #1 will be retrieved. This can be changed with the --board= and --axis= 
    command line options.

  RELEASE HISTORY
	Copyright (c) 2015 by Precision Micro Control Corp. All rights reserved.

	$Id: init.py 921 2015-06-23 18:16:19Z brian $

	Version 4.4.1		23-Jun-15		Programmer: R. Brian Gaynor
	  - First release

"""
import getopt, sys
from mcapi import *
from mcdlg import *

# command line parsing
try:
	opts, args = getopt.getopt(sys.argv[1:], "a:b:", ["axis=", "board="])
except getopt.GetoptError as err:
	print(str(err))
	Usage()
	sys.exit(2)

axis = 1
id = 0
verbose = False
for o, a in opts:
	if o in ("-a", "--axis"):
		axis = int(a)
	elif o in ("-b", "--board"):
		id = int(a)

# create a controller and dialog objects
ctlr = Mcapi()
mcdlg = Mcdlg()

 # open the controller at ID #0
if ctlr.Open(0, MC_OPEN_BINARY) > 0:

	# get controller settings
	param = MCPARAMEX()
	ctlr.GetConfigurationEx(param)

	axis_cfg = MCAXISCONFIG()
	ctlr.GetAxisConfiguration(axis, axis_cfg)

	print()
	print("Opened controller #0, a ", mcdlg.ControllerDescEx(param.ControllerType, MCDLG_DESCONLY), ".", sep="")
	print("Controller information is available in the structure 'param' and axis")
	print("information for axis #", axis, " is in the structure 'axis_cfg'. The object 'ctlr' may", sep="")
	print("be used to send motion conmmands to this controller and object 'mcdlg' may be")
	print("used to invoke the Motion Dialog functions.")
	print()
	print("    Example:    pos = ctlr.GetPositionEx(axis)")
	print("                ctlr.EnableAxis(axis, True)")
	print("                ctlr.Close()                     # call before exiting")
	print()

else:
	print("Problem opening controller")

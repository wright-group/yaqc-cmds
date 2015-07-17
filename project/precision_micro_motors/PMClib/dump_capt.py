"""

  NAME
	dump_capt.py - reads the captured data from an axis and outputs as comma separated values

  DESCRIPTION
    This script will retrieve one or more sets of captured data points from a controller
    and send them to the console as comma separated values. From the console it is easy to
    redirect the CSV data into a file, which may then be imported directly to a variety of
    programs - spreadsheet, numerical analysis, etc.

  EXAMPLES
    Dump all of the data from board ID 0, axis #1 to the console:

      python bump_capt.py

    Dump the first 100 points from board ID 0, axis #5 to the file test.csv:

      python bump_capt.py --axis=5 --points=100 > test.csv

    Dump the second 100 points from board ID 0, axis #5 to the file test.csv:

      python bump_capt.py --axis=5 --points=100 --start=100 > test.csv

    Get information about the capture support for axis #3:

      python bump_capt.py --axis=3 --info

    Dump the all points from board ID 0, axis #7 and instead of a time value in the first
    column just give a simple index (1, 2, 2, etc.):

      python bump_capt.py --axis=7 --index

  RELEASE HISTORY
	Copyright (c) 2015 by Precision Micro Control Corp. All rights reserved.

	$Id: dump_capt.py 921 2015-06-23 18:16:19Z brian $

	Version 4.4.1		23-Jun-15		Programmer: R. Brian Gaynor
	  - First release

"""
import getopt, sys
from mcapi import *
from mccl import *

def main():
	# command line parsing
	try:
		opts, args = getopt.getopt(sys.argv[1:], "a:b:ifp:s:h", ["axis=", "board=", "index", "info", "points=", "start=", "help"])
	except getopt.GetoptError as err:
		print(str(err))
		Usage()
		sys.exit(2)

	axis = 1			# axis number to dump
	id = 0				# id of controller to use
	index = False		# if true use numeric index in place of time in column one of the output
	info = False		# if true we print out info about axis capture mode and exit
	points = 0			# number of points to dump
	start = 0			# starting point number

	for o, a in opts:
		if o in ("-a", "--axis"):
			axis = int(a)
		elif o in ("-b", "--board"):
			id = int(a)
		elif o in ("-i", "--index"):
			index = True
		elif o in ("-f", "--info"):
			info = True
		elif o in ("-p", "--points"):
			points = int(a)
		elif o in ("-s", "--start"):
			start = int(a)
		elif o in ("-h", "--help"):
			Usage()
			sys.exit()

	# create a controller object and open a controller 
	ctlr = Mcapi()
	err = ctlr.Open(id, MC_OPEN_BINARY)

	if err > 0:
		param = MCPARAMEX()
		ctlr.GetConfigurationEx(param)

		# range check parameters
		if param.NumberAxes < 1:
			print("ERROR: No axes were detected on this controller")
			ctlr.Close()
			sys.exit(1)

		if axis < 1 or axis > param.NumberAxes:
			print("ERROR: Axis #", axis, " is out of range (1 - ", param.NumberAxes, ")", sep="")
			ctlr.Close()
			sys.exit(1)

		# axis settings
		axis_cfg = MCAXISCONFIG()
		ctlr.GetAxisConfiguration(axis, axis_cfg)

		# capture settings
		actual_points, actual_period, actual_delay, actual_index = ctlr.GetCaptureSettings(axis)

		if info:
			print()
			print("Axis", axis, "capture buffer size is", axis_cfg.CapturePoints, "points")
			print("Capture modes: MC_CAPTURE_ACTUAL, MC_CAPTURE_ERROR, MC_CAPTURE_OPTIMAL,")
			print("\tMC_CAPTURE_TORQUE", end="")
			if axis_cfg.CaptureModes & MC_CAPTURE_AUXILIARY:
				print(", MC_CAPTURE_AUXILIARY", end="")
			if axis_cfg.CaptureModes & MC_CAPTURE_STATUS:
				print(", MC_CAPTURE_STATUS", end="")
			print()
			print("Current capture points:", actual_points)
			print("Current capture period:", actual_period, "sec")
			print("Current capture delay: ", actual_delay, "sec")
			ctlr.Close()
			sys.exit()

		if points == 0:
			if actual_points > 0:
				points = actual_points				# default to actual number of points captured, if known
			else:
				points = axis_cfg.CapturePoints		# else default to capture size
		if points < 1 or points > axis_cfg.CapturePoints:
			print("ERROR: Points value of ", points, " is out of range (1 - ", axis_cfg.CapturePoints, ")", sep="")
			ctlr.Close()
			sys.exit(1)

		if start < 0 or start > axis_cfg.CapturePoints - 1:
			print("ERROR: Starting point value of ", start, " is out of range (0 - ", axis_cfg.CapturePoints - 1, ")", sep="")
			ctlr.Close()
			sys.exit(1)

		if start + points > axis_cfg.CapturePoints:
			print("ERROR: Start of ", start, " plus number of points of ", points, " combined is out of range", sep="")
			ctlr.Close()
			sys.exit(1)

		# get data from controller
		actual = ctlr.GetCaptureData(axis, MC_CAPTURE_ACTUAL, start, points)
		optimal = ctlr.GetCaptureData(axis, MC_CAPTURE_OPTIMAL, start, points)
		torque = ctlr.GetCaptureData(axis, MC_CAPTURE_TORQUE, start, points)
		if axis_cfg.CaptureModes & MC_CAPTURE_AUXILIARY:
			aux = ctlr.GetCaptureData(axis, MC_CAPTURE_AUXILIARY, start, points)
		if axis_cfg.CaptureModes & MC_CAPTURE_STATUS:
			status = ctlr.GetCaptureData(axis, MC_CAPTURE_STATUS, start, points)

		# print to console in csv format
		if actual_period > 0.0 and index == False:
			print("Time, Actual, Optimal, Error, Torque", end="")
		else:
			print("Index, Actual, Optimal, Error, Torque", end="")
		if axis_cfg.CaptureModes & MC_CAPTURE_AUXILIARY:
			print(", Aux. Enc.", end="")
		if axis_cfg.CaptureModes & MC_CAPTURE_STATUS:
			print(", Status", end="")
		print()

		for i in range(0, points):
			if actual_period > 0.0 and index == False:
				print("{0:.6f}".format((i + start) * actual_period + actual_delay), end="")
			else:
				print(i + start, end="")
			print(", ", actual[i], ", ", optimal[i], ", ", actual[i] - optimal[i], ", ", torque[i], sep="", end="")
			if axis_cfg.CaptureModes & MC_CAPTURE_AUXILIARY:
				print(", ", aux[i], sep="", end="")
			if axis_cfg.CaptureModes & MC_CAPTURE_STATUS:
				print(", ", "0x{:02X}".format(status[i]), sep="", end="")
			print()

		ctlr.Close()
	else:
		print("Error", err, " while attempting to open controller", device_id);

#
# Command line usage
#
def Usage():
	print()
	print("Usage: python dump_capt.py [OPTIONS]")
	print("Dump motion controller capture data as comma separated values.")
	print("  -a, --axis=NUM     dump axis 'NUM', default is one (1).")
	print("  -b, --board=NUM    use controller 'NUM', default is zero (0).")
	print("  -i, --index        force numeric index in column 1 instead of time.")
	print("  -f, --info         display capture support info for axis.")
	print("  -p, --points=NUM   number of points to dump, default is controller max.")
	print("  -s, --start=NUM    starting point to dump, default is zero (0).")
	print("  -h, --help         display this help and exit.")

#
# Run main()
#
if __name__ == "__main__":
	main()

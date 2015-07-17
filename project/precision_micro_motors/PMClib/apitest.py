"""

  NAME
	apitest.py - a python port of the c-language MCAPI test code

  DESCRIPTION
    This code tests and reports on many of the function in the Motion Control
    API. It doesn't provide 100% coverage, but it does cover a lot of the most
    used API functions. Note that this test will change the axis under test 
    settings in different (and probably useless) state.

  RELEASE HISTORY
	Copyright (c) 2015 by Precision Micro Control Corp. All rights reserved.

	$Id: apitest.py 924 2015-06-23 21:16:53Z brian $

	Version 4.4.1		23-Jun-15		Programmer: R. Brian Gaynor
	  - First release

"""
import getopt, math, sys
from mcapi import *
from mccl import *

def main():
	# command line parsing
	try:
		opts, args = getopt.getopt(sys.argv[1:], "a:b:vh", ["axis=", "board=", "verbose", "help"])
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
		elif o in ("-v", "--verbose"):
			verbose = True
		elif o in ("-h", "--help"):
			Usage()
			sys.exit()

	# create a controller object and open a controller 
	ctlr = Mcapi()
	err = ctlr.Open(id, MC_OPEN_BINARY)

	if err > 0:
		print("Motion Control API Test v4.4")

		param = MCPARAMEX()
		ctlr.GetConfigurationEx(param)
		print("  Controller Type:\t", param.ControllerType)

		axis_cfg = MCAXISCONFIG()
		ctlr.GetAxisConfiguration(axis, axis_cfg)
		if axis_cfg.MotorType & MC_TYPE_SERVO:
			print("  Test Axis Type:\t", axis_cfg.ModuleType, " (a servo axis)")
		else:
				print("  Test Axis Type:\t", axis_cfg.ModuleType, " (a stepper axis)")
		print("==========")

		# run tests
		errors = 0
		errors += OpenCloseTest(ctlr, axis, param, axis_cfg, verbose)
		errors += GetSetTest(ctlr, axis, param, axis_cfg, verbose)
		errors += IOTest(ctlr, axis, param, axis_cfg, verbose)
		errors += OEMTest(ctlr, axis, param, axis_cfg, verbose)
		errors += MacroTest(ctlr, axis, param, axis_cfg, verbose)
		errors += StatusWordTest(ctlr, axis, axis_cfg, param, verbose)
		errors += LimitTest(ctlr, axis, param, axis_cfg, verbose)
		errors += ScaleTest(ctlr, axis, param, axis_cfg, verbose)

		ctlr.Close()
	else:
		print("Error", err, " while attempting to open controller", device_id);

#
# Check results from a set then get operation, print message as needed
#
def check_results(error, setval, getval, prompt, verbose):
	if getval != setval:
		error += 1
		if error == 1:
			print("Failed")
		if verbose:
			print("  Error: expected", prompt, "of", setval, "/ actual ", getval)
	return error

#
#  get_set_double - helper function to do actual get/set testing of MCAPI functions that
#                   have a double precision argument (in addition to the controller handle
#                   and axis number). 
#
def get_set_double(ctlr, axis, verbose, get, set):
	error = 0
	orig_value = get(axis)

	for i in range(1, 11):
		get_value = 0.0
		set_value = math.floor(12345.0 / i)

		try:
			set(axis, set_value)
			get_value = get(axis)
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)
		error = check_results(error, set_value, get_value, "", verbose)

	set(axis, orig_value)

	if error == 0:
		print("Passed")

	return error

#
# Process errors helper
#
def process_error(msg, error, verbose):
		if error == 1:
			print("Failed")
		if verbose:
			print("    MCAPI Error: ", msg)

#
# GetSetTest - set and get parameters test.
#
def GetSetTest(ctlr, axis, param, axis_cfg, verbose):
	print("Get/Set Parameter Functions")

	error = 0
	error_total = 0
	get_value = 0		# make sure this is assigned some value now in case we get an exception later

	ctlr.EnableAxis(axis, False)
	
	# accel
	print("  Acceleration..........................", end="")
	error_total += get_set_double(ctlr, axis, verbose, ctlr.GetAccelerationEx, ctlr.SetAcceleration)

	# aux encoder (optional)
	print("  Auxiliary Encoder.....................", end="")
	ctlr.SetAuxEncPos(axis, 0.0)
	if ctlr.GetError() == MCERR_NOTSUPPORTED:
		print("Not supported")
	else:
		error_total += get_set_double(ctlr, axis, verbose, ctlr.GetAuxEncPosEx, ctlr.SetAuxEncPos)
	
	# decel
	print("  Deceleration..........................", end="")
	error_total += get_set_double(ctlr, axis, verbose, ctlr.GetDecelerationEx, ctlr.SetDeceleration)
	
	# gain
	print("  Gain..................................", end="")
	if axis_cfg.MotorType & MC_TYPE_SERVO:
		error_total += get_set_double(ctlr, axis, verbose, ctlr.GetGain, ctlr.SetGain)
	else:
		print("Not supported")

	# output mode
	print("  Output Mode...........................", end="")
	for set_value in [MC_OM_BIPOLAR, MC_OM_UNIPOLAR, MC_OM_PULSE_DIR, MC_OM_CW_CCW, MC_OM_BI_PWM, MC_OM_UNI_PWM]:
		try:
			ctlr.SetModuleOutputMode(axis, set_value)
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)

	if error == 0:
		print("Passed")
	else:
		error_total += error
		error = 0

	# phase
	print("  Phase.................................", end="")
	for set_value in [MC_PHASE_STD, MC_PHASE_REV]:
		try:
			ctlr.SetServoOutputPhase(axis, set_value)
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)

		try:
			get_value = ctlr.GetServoOutputPhase(axis)
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)
			error = check_results(error, set_value, get_value, "phase value", verbose)

	if error == 0:
		print("Passed")
	else:
		error_total += error
		error = 0

	# position
	print("  Position..............................", end="")
	error_total += get_set_double(ctlr, axis, verbose, ctlr.GetPositionEx, ctlr.SetPosition)

	# profiles
	print("  Profiles..............................", end="")
	if param.CanChangeProfile: 
		for set_value in [MC_PROF_TRAPEZOID, MC_PROF_SCURVE, MC_PROF_PARABOLIC]:
			try:
				ctlr.SetProfile(axis, set_value)
			except McapiException as msg:
				error += 1
				process_error(msg, error, verbose)

			try:
				get_value = ctlr.GetProfile(axis)
			except McapiException as msg:
				error += 1
				process_error(msg, error, verbose)
			error = check_results(error, set_value, get_value, "profile value", verbose)

		if error == 0:
			print("Passed")
		else:
			error_total += error
			error = 0
	else:
		print("Not supported")

	# register
	print("  Register..............................", end="")
	for i in range(30, 40):
		set_value = int(12345678 / i)
		try:
			ctlr.SetRegister(i, set_value, MC_TYPE_LONG)
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)

		try:
			get_value = ctlr.GetRegister(i, MC_TYPE_LONG)
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)
		error = check_results(error, set_value, get_value, "register value", verbose)

	if error == 0:
		print("Passed")
	else:
		error_total += error
		error = 0

	# torque
	print("  Torque................................", end="")
	if axis_cfg.MotorType & MC_TYPE_SERVO:
		error_total += get_set_double(ctlr, axis, verbose, ctlr.GetTorque, ctlr.SetTorque)
	else:
		print("Not supported")

	# vector velocity (optional)
	print("  Vector Velocity.......................", end="")
	try:
		ctlr.SetVectorVelocity(axis, 1.0)
	except McapiException as msg:
		error += 1
		process_error(msg, error, verbose)

	if error == 0:
		if ctlr.GetError() == MCERR_NOTSUPPORTED:
			print("not supported")
		else:
			error_total += get_set_double(ctlr, axis, verbose, ctlr.GetVectorVelocity, ctlr.SetVectorVelocity)
	else:
		error_total += error
		error = 0

	# velocity
	print("  Velocity..............................", end="")
	error_total += get_set_double(ctlr, axis, verbose, ctlr.GetVelocityEx, ctlr.SetVelocity)
	
	return error_total

#
# IOTest - digital and analog I/O functions test
#
def IOTest(ctlr, axis, param, axis_cfg, verbose):
	print("General Purpose I/O Functions")

	error = 0
	
	# analog
	print("  Testing Analog I/O....................", end="")
	for i in range(1, 5):
		try:
			ctlr.GetAnalogEx(i)
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)

	if error == 0:
		print("Passed")
	else:
		error_total += error
		error = 0

	# digital I/O
	print("  Testing Digital I/O...................", end="") 

	if param.ControllerType == MFXPCI1000:		# Multiflex has differnet channel assignments from other PMC controllers
		start = 33			# start of MFXPCI1 outputs
		stop = 48
	else:
		start = 9			# channels 9-16 are or can be configured as outputs on everything except the Multiflex
		stop = 16
	
	for i in range(start, stop + 1):
		try:
			ctlr.ConfigureDigitalIO(i, MC_DIO_OUTPUT)
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)

	# all off
	for i in range(start, stop + 1):
		try:
			ctlr.EnableDigitalIO(i, False)
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)
	
	for i in range(start, stop + 1):
		try:
			if ctlr.GetDigitalIOEx(i) != 0: 
				print("  Error: channel", i, "expected off")
				error += 1
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)

	# all on	
	for i in range(start, stop + 1):
		try:
			ctlr.EnableDigitalIO(i, True)
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)

	for i in range(start, stop + 1):
		try:
			if ctlr.GetDigitalIOEx(i) != 1: 
				print("  Error: channel", i, "expected on")
				error += 1
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)

	if error == 0:
		print("Passed")
	return error

#
# LimitTest - test hard and (optionally) soft limits 
#
def LimitTest(ctlr, axis, param, axis_cfg, verbose):
	print("Hard/Soft Limits")

	error = 0
	
	#  hard limits
	print("  Hard Limits...........................", end="")

	try:
		sHMode = MC_LIMIT_BOTH | MC_LIMIT_SMOOTH
		ctlr.SetLimits(axis, sHMode, 0, 0.0, 0.0)
		gHMode, gSMode, gSMinus, gSPlus = ctlr.GetLimits(axis)
	except McapiException as msg:
		error += 1
		process_error(msg, error, verbose)
	error = check_results(error, sHMode, gHMode, "hard limit mode", verbose)

	try:
		sHMode = MC_LIMIT_PLUS | MC_LIMIT_ABRUPT
		ctlr.SetLimits(axis, sHMode, 0, 0.0, 0.0)
		gHMode, gSMode, gSMinus, gSPlus = ctlr.GetLimits(axis)
	except McapiException as msg:
		error += 1
		process_error(msg, error, verbose)
	error = check_results(error, sHMode, gHMode, "hard limit mode", verbose)

	try:
		sHMode = MC_LIMIT_OFF
		ctlr.SetLimits(axis, sHMode, 0, 0.0, 0.0)
		gHMode, gSMode, gSMinus, gSPlus = ctlr.GetLimits(axis)
	except McapiException as msg:
		error += 1
		process_error(msg, error, verbose)
	error = check_results(error, sHMode, gHMode, "hard limit mode", verbose)

	if error == 0:
		print("Passed")

	# soft limits
	if param.SoftLimits:
		print("  Soft Limits...........................", end="")

		try:
			sSMode = MC_LIMIT_PLUS | MC_LIMIT_ABRUPT
			ctlr.SetLimits(axis, 0, sSMode, 0.0, 0.0)
			gHMode, gSMode, gSMinus, gSPlus = ctlr.GetLimits(axis)
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)
		error = check_results(error, sSMode, gSMode, "soft limit mode", verbose)

		try:
			sSMode = MC_LIMIT_BOTH
			ctlr.SetLimits(axis, 0, sSMode, 0.0, 0.0)
			gHMode, gSMode, gSMinus, gSPlus = ctlr.GetLimits(axis)
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)
		error = check_results(error, sSMode, gSMode, "soft limit mode", verbose)

		try:
			sSMode = MC_LIMIT_BOTH | MC_LIMIT_SMOOTH
			ctlr.SetLimits(axis, 0, sSMode, 100.0, 250.0)
			gHMode, gSMode, gSMinus, gSPlus = ctlr.GetLimits(axis)
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)

		if gSMinus != 100.0 or gSPlus != 250.0: 
			error += 1
			if error == 1:
				print("Failed")
			if verbose:
				print("  Error: soft limit value")

		ctlr.SetLimits(axis, 0, MC_LIMIT_OFF, 0.0, 0.0)

		if error == 0:
			print("Passed")
	return error

#
# MacroTest - test asccii macro functionality. 
#
def MacroTest(ctlr, axis, param, axis_cfg, verbose):
	print("Macro/Block Functions")

	error = 0
	Test1Value = 123
	Test2Value = 246

	#			
	# 1st test
	#
	print("  Macro/Block Test 1....................", end="")
	
	# reset macros
	try:
		ctlr.BlockBegin(MC_BLOCK_RESETM, 0)
	except McapiException as msg:
		error += 1
		process_error(msg, error, verbose)

	# create a macro, run it, and check results	
	try:
		ctlr.BlockBegin(MC_BLOCK_MACRO, 1);					# create macro to set accumulator to "Test1Value"
		ctlr.SetRegister(0, Test1Value, MC_TYPE_LONG);
		ctlr.BlockEnd()

		ctlr.SetRegister(0, 0, MC_TYPE_LONG)				# clear accumulator
		ctlr.MacroCall(1)									# run macro
		value = ctlr.GetRegister(0, MC_TYPE_LONG)			# check that macro ran/changed value of accumulator

	except McapiException as msg:
		error += 1
		process_error(msg, error, verbose)
	
	if value != Test1Value:
		error += 1
		if error == 1:
			print("Failed")
		if verbose:
			print("  Error: macro failed to run")

	if error == 0:
		print("Passed")
	
	#			
	# 2nd test
	#
	print("  Macro/Block Test 2....................", end="")

	# reset macros
	try:
		ctlr.BlockBegin(MC_BLOCK_RESETM, 0)
	except McapiException as msg:
		error += 1
		process_error(msg, error, verbose)


	# create a macro, run it, and check results	
	try:
		ctlr.SetRegister(0, Test2Value, MC_TYPE_LONG)

		ctlr.BlockBegin(MC_BLOCK_MACRO, 1);					# create macro to multiply accumulator by 2 - 3 times
		ctlr.pmccmdex(0, AM, 2, MC_TYPE_LONG)
		ctlr.Repeat(2);
		ctlr.BlockEnd()

		ctlr.SetRegister(0, Test2Value, MC_TYPE_LONG);		# set accumulator to Test2Value
		ctlr.MacroCall(1);									# run macro
		value = ctlr.GetRegister(0, MC_TYPE_LONG)			# check that macro ran/changed value of accumulator

	except McapiException as msg:
		error += 1
		process_error(msg, error, verbose)

	if value != Test2Value * 8: 
		error += 1
		if error == 1:
			print("Failed")
		if value == Test1Value:
			print("  Error: reset macros failed")
		else:
			print("  Error: macro failed to run")

	if error == 0:
		print("Passed")
	return error

#
# OEMTest - test low-level oem functions. 
#
def OEMTest(ctlr, axis, param, axis_cfg, verbose):
	print("OEM Functions") 

	error = 0

	# pmccmdex / pmcrpyex
	print("  Command / Reply.......................", end="") 
	try:
		value = 1
		ctlr.pmccmdex(0, TC, value, MC_TYPE_LONG)
	except McapiException as msg:
		error += 1
		process_error(msg, error, verbose)

	try:
		ctlr.pmcrpyex(MC_TYPE_LONG)	
	except McapiException as msg:
		error += 1
		process_error(msg, error, verbose)
	if error == 0:
		print("Passed")

	# pmcputs / pmcgets
	print("  Puts / Gets...........................", end="") 
	ctlr.Reopen(MC_OPEN_ASCII)
	try:
		ctlr.pmcputs(b"TC1\r")
	except McapiException as msg:
		error += 1
		process_error(msg, error, verbose)

	buffer = create_string_buffer(255)	
	try:
		ctlr.pmcgets(buffer, getsizeof(buffer))
	except McapiException as msg:
		error += 1
		process_error(msg, error, verbose)
	ctlr.pmcgets(buffer, getsizeof(buffer))		# extra flush
	
	# finish    
	ctlr.Reopen(MC_OPEN_BINARY)

	if error == 0:
		print("Passed")
	return error

#
# OpenCloseTest - handle open / close tests. Assumes that the handle passed is the only 
#                 open handle to the controller (i.e. handle #1). 
#
def OpenCloseTest(ctlr, axis, param, axis_cfg, verbose):
	print("Handle Open/Close/Reopen................", end="")

	error = 0

	# check for incrementing handles
	temp1 = Mcapi() 
	temp1.Open(param.ID, MC_OPEN_BINARY)
	if temp1.Handle() <= ctlr.Handle():
		if ++error == 1:
			print("Failed")
		if verbose:
			print("  Error: Invalid handle opening second handle")
	old_handle = temp1.Handle()		# remember the handle number
	temp1.Close()

	# check that previous close worked (handle recycled)
	temp2 = Mcapi() 
	temp2.Open(param.ID, MC_OPEN_BINARY)
	if old_handle != temp2.Handle(): 
		if ++error == 1:
			print("Failed")
		if verbose:
			print("  Error: MCClose() failed")
	temp2.Close()

	# check reopen - (change to excusive)
	ctlr.Reopen(MC_OPEN_BINARY | MC_OPEN_EXCLUSIVE)
	temp1.Open(param.ID, MC_OPEN_BINARY)
	if temp1.Handle() > 0: 
		if ++error == 1:
			print("Failed")
		if verbose:
			print("  Error: Reopened busy handle in 'Exclusive' mode")
		MCClose(hCtlr1);

	# finish (remove exclusive mode)
	ctlr.Reopen(MC_OPEN_BINARY)

	if error == 0:
		print("Passed")
	return error

#
# ScaleTest - scaling functions test. 
#
def ScaleTest(ctlr, axis, param, axis_cfg, verbose):
	error = 0

	if param.CanDoScaling: 
		print("Scaling Functions.......................", end="")

		Scale = MCSCALE()
		Results = MCSCALE()

		try:
			Scale.Constant = 10.0
			Scale.Offset = 20.0
			Scale.Rate = 30.0
			Scale.Scale = 40.0
			Scale.Zero = 50.0
			Scale.Time = 1.0
			ctlr.EnableAxis(axis, False)
			ctlr.SetScale(axis, Scale)
			ctlr.EnableAxis(axis, True)
			ctlr.GetScale(axis, Results)
		except McapiException as msg:
			error += 1
			process_error(msg, error, verbose)

		if axis_cfg.MotorType & MC_TYPE_SERVO:
			error = check_results(error, Scale.Constant, Results.Constant, "Scale.Constant", verbose)	# servo only
		error = check_results(error, Scale.Offset, Results.Offset, "Scale.Offset", verbose)
		error = check_results(error, Scale.Rate, Results.Rate, "Scale.Rate", verbose)
		error = check_results(error, Scale.Scale, Results.Scale, "Scale.Scale", verbose)
		error = check_results(error, Scale.Zero, Results.Zero, "Scale.Zero", verbose)

		if error == 0:
			print("Passed")

	else:
		print("Not supported")
	
	return error

#
# StatusWordTest - test status word functions
#
def StatusWordTest(ctlr, axis, param, axis_cfg, verbose):
	print("Status Word Functions...................", end="")

	error = 0
	
	ctlr.EnableAxis(axis, False)
	if ctlr.DecodeStatus(ctlr.GetStatus(axis), MC_STAT_MTR_ENABLE) == 1: 
		error += 1
		if error == 1:
			print("Failed")
		if verbose:
			print("  Error: expected motor off")
	
	ctlr.EnableAxis(axis, True)
	if ctlr.DecodeStatus(ctlr.GetStatus(axis), MC_STAT_MTR_ENABLE) != 1: 
		error += 1
		if error == 1:
			print("Failed")
		if verbose:
			print("  Error: expected motor on")

	if error == 0:
		print("Passed")
	return error

#
# Command line usage
#
def Usage():
	print()
	print("Usage: python apitest.py [OPTIONS]")
	print("The PMC Motion Control API test program.")
	print("Mandatory arguments to long options are mandatory for short options too.")
	print("  -a, --axis=NUM     test using axis 'NUM', default is one (1).")
	print("  -b, --board=NUM    open controller 'NUM', default is zero (0).")
	print("  -v, --verbose      enable detailed messages, default is disabled.")
	print("  -h, --help         display this help and exit.")

#
# Run main()
#
if __name__ == "__main__":
	main()

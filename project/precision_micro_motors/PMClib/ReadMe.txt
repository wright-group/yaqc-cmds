
              ----------------------------------------------------
                          Precision MicroControl Corp.
                     MCAPI Python Library - Version 4.4.1
                          23-Jun-2015  *  ReadMe File
                $Id: ReadMe.txt 920 2015-06-23 17:21:49Z brian $
              ----------------------------------------------------


The MCAPI Python Library is a binding of PMC's Motion Control API to the
interpreted Python language, making it possible to experiment with the 
MCAPI functions interactively and protoype machine applications more quickly.

The plan is to fully release this library as part of the normal MCAPI 
distribution in version 4.5.0 (the next planned release). Until then this 
library should be considered a BETA. While it is very unlikely that there 
would be major changes it is possible a few functions may be further tweaked
before the 4.5.0 release.

Linux users should be aware that this version does not yet Linux versions of
the MCAPI (there is an issue with some cross-linking in the MCAPI libraries
that python doesn't like). This should be resolved in MCAPI 4.5.0.



Index
=====
1. Revision History
2. General Design Concepts 
3. The Python Scripts



Revision History
=================
Version 4.4.1
-------------
New features
  - First Release



General Design Concepts
=======================
* This implementation is intended for Python version 3 or later.


* Like our .NET assembly for MCAPI the python binding uses a class to "hold"
  the controller handle and expose the normal MCAPI functions as methods of 
  the class. In python to read the position of axis 5:

	ctlr = Mcapi()
	ctlr.Open(0, MC_OPEN_BINARY, None)
	pos = ctlr.GetPositionEx(5)

  equivalent in C:

	double pos;
	handle = MCOpen(0, MC_OPEN_BINARY, "")
	MCGetPositionEx(Handle, 5, &pos)


* Also similar to our .NET implementation (which uses a containing class) the
  leading "MC" on MCAPI functions has been removed. In pure function libraries
  the leading MC helps to make sure the function names are unique, this is
  unnecessary (and wordy) when the functions are member functions of an class. 
  The C equivalent:

	MCGetPositionEx(handle, 5, &pos);

  becomes (in Python):

	pos = ctlr.GetPositionEx(5)


* The Mcapi python class handles all errors via exceptions instead of returning
  error codes like the older functional language bindings (e.g. C). This allows 
  us to simplify the calling parameters of functions that return a value and 
  avoid ugly hacks to make them work in Python as they should work in Python:

	MCGetPositionEx(handle, axis, &pos);

  becomes

	pos = ctlr.GetPositionEx(axis)

  This means that many of the regular MCAPI functions have simplified parameter 
  lists when compared to their functional equivalents.


* All of the MCAPI structures (e.g. MCPARAMEX) are implemented as classes. as a
  result any that require a size member to be correctly set before the 
  structure may be used in a MCAPI call will have that size automatically set 
  in their constructor (no need to set cbSize by the user).


* The MCAPI uses ASCII c-strings, where possible the MCAPI Python class
  converts these to Unicode strings (which is what Python uses natively). If 
  needed, use the decode() member function of the bytes type to convert an 
  ASCII c-string to unicode. The TranslateErrorEx() Mcapi function in mcapi.py
  has an example of this.



The Python Scripts
==================

apitest.py
  This is a python port of the C++ apitest application supplied with Linux 
  versions of the MCAPI. It provides testing of many (not all) of the primary 
  Motion Control API functions.

benchmark.py
  A python implementation of our standard benchmarking utility. During 
  development this was used to verify that the python code performace for
  MCAPI functions was close (roughly 95%) to that of native executable 
  code (.EXE).

dump_capture.py 
  A python command line utility to read out the capture data buffers of an
  axis and dump the values to the console as comma separated values. Programs
  like Servo Tuning use the capture buffers to capture a move sequence and 
  display the move data (user applications can also command the controller to
  capture move data). Often the plotter utility is all that is needed to 
  examine this data but sometimes people want to feed that data into another
  application for analysis. dump_capture.py is perfect for this.

init.py
  To simplify working interactively with the MCAPI pyhon code the init.py
  script may be used to setup the python environement so that it is "ready 
  to go" (needed libraries imported, controller and dialog objects
  created, configuration data retrieved):

    C:\>python - i init.py

    >>> ctlr.GetPositionEx()
    1234.0
    >>> 

mcapi.py
  The python wrapper class for the Motion Control API.

mccl.py
  Defines mnemonics for the MCCL command codes (only needed if your are using
  MCCL commamds that are not otherwise supported by the MCAPI).

mcdlg.py
  The python wrapper class for the Motion Dialog functions.

pyDemo.py
  A python implementation of our CWDemo.exe C++ sample program. Demostrates
  a complete python sample with GUI (TK).

simple-sample.py
  The simplest sample program, opens a controller, determines how many motor 
  axes are available, and prints the current position of each axis.
  
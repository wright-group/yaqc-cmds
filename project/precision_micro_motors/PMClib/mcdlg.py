"""

  NAME
    mcdlg.py - Motion Control API setup dialogs for python

  DESCRIPTION
    Include this class library in your python application to use the MCAPI 
    motion dialog functions.

    from mcdlg import *

  RELEASE HISTORY
    Copyright (c) 2015 by Precision Micro Control Corp. All rights reserved.

    $Id: mcdlg.py 921 2015-06-23 18:16:19Z brian $

    Version 4.4.1		23-Jun-15		Programmer: R. Brian Gaynor
      - First release.

"""
from ctypes import *
from ctypes.wintypes import HWND
from mcapi import *

#
# MCDLG_RestoreAxis / MCDLG_SaveAxis / MCDLG_ConfigureAxis flags
#
MCDLG_PROMPT			= 0x0001			# save / restore
MCDLG_NOMOTION			= 0x0002			# save / restore / configure
MCDLG_NOFILTER			= 0x0004			# save / restore / configure
MCDLG_NOPHASE			= 0x0008			# save / restore
MCDLG_NOPOSITION		= 0x0010			# save / restore / configure
MCDLG_NOSCALE			= 0x0020			# save / restore
MCDLG_NOHARDLIMITS		= 0x0040			# configure
MCDLG_NOSOFTLIMITS		= 0x0080			# configure
MCDLG_NORATES			= 0x0100			# configure
MCDLG_NOPROFILES		= 0x0200			# save / restore / configure
MCDLG_NOMISC			= 0x0400			# configure
MCDLG_CHECKACTIVE		= 0x0800			# configure / restore
MCDLG_NOOUTPUTMODE		= 0x1000			# save / restore / configure

#
# MCDLG_ControllerDesc / MCDLG_ModuleDesc flags
#
MCDLG_NAMEONLY			= 0x0001
MCDLG_DESCONLY			= 0x0002

#
# Define a Mcdlg exception class
#
class McdlgException(Exception):
	def __init__(self, arg):
		# Set some exception infomation
		self.msg = arg

#
# The main MCapi object (all the public access is in this class)
#
class Mcdlg:
	# Motion Control Dialogs
	def __init__(self):
		# windows
		if architecture()[1] == 'WindowsPE':
			if architecture()[0] == '32bit':
				self._dll = windll.mcdlg32
			else:
				self._dll = windll.mcdlg64
		else:
			print("Unsupported platform", architecture())

		#
		# MCDLG function argument and return type declarations. It would be nice if these could be in their 
		# respective member function but there is about a 12% performance penalty if they are run every time a
		# function is called (because python is interpreted). In __init__ they only run once.
		#
		self._dll.MCDLG_AboutBox.argtypes = [HWND, c_char_p, c_int]
		self._dll.MCDLG_CommandFileExt.argtypes = [c_int, c_int, c_char_p, c_int]
		self._dll.MCDLG_CommandFileExt.restype = c_char_p
		self._dll.MCDLG_ConfigureAxis.argtypes = [HWND, HCTRLR, c_ushort, c_int, c_char_p]
		self._dll.MCDLG_ControllerDescEx.argtypes = [c_int, c_int, c_char_p, c_int]
		self._dll.MCDLG_ControllerDescEx.restype = c_char_p
		self._dll.MCDLG_ControllerInfo.argtypes = [HWND, HCTRLR, c_int, c_char_p]
		self._dll.MCDLG_DownloadFile.argtypes = [HWND, HCTRLR, c_int, c_char_p]
		self._dll.MCDLG_ListControllers.argtypes = [POINTER(c_short), c_short]
		self._dll.MCDLG_ModuleDescEx.argtypes = [c_int, c_int, c_char_p, c_int]
		self._dll.MCDLG_ModuleDescEx.restype = c_char_p
		self._dll.MCDLG_RestoreAxis.argtypes = [HCTRLR, c_ushort, c_int, c_char_p]
		self._dll.MCDLG_RestoreDigitalIO.argtypes = [HCTRLR, c_ushort, c_ushort, c_char_p]
		self._dll.MCDLG_SaveAxis.argtypes = [HCTRLR, c_ushort, c_int, c_char_p]
		self._dll.MCDLG_SaveDigitalIO.argtypes = [HCTRLR, c_ushort, c_ushort, c_char_p]
		self._dll.MCDLG_Scaling.argtypes = [HWND, HCTRLR, c_ushort, c_int, c_char_p]
		self._dll.MCDLG_SelectController.argtypes = [HWND, c_short, c_int, c_char_p]
		self._dll.MCDLG_SelectController.restype = c_short

	def AboutBox(self, hwnd, title, bitmap_id):
		"""Display a simple About Box with application and MCAPI version info."""
		return self._dll.MCDLG_AboutBox(hwnd, title, bitmap_id)

	def CommandFileExt(self, type, flags):
		"""Get the MCCL file extension for a particular controller model."""
		buffer = create_string_buffer(256)
		self._dll.MCDLG_CommandFileExt(type, flags, buffer, 256)
		return buffer.value.decode()

	def ConfigureAxis(self, hwnd, controller, axis, flags, title):
		"""Display a standardized axis configuration dialog."""
		return self._dll.MCDLG_ConfigureAxis(hwnd, controller.Handle(), axis, flags, title)

	def ControllerDescEx(self, type, flags):
		"""Get a short or long text description for a controller model."""
		buffer = create_string_buffer(256)
		self._dll.MCDLG_ControllerDescEx(type, flags, buffer, 256)
		return buffer.value.decode()

	def ControllerInfo(self, hwnd, controller, flags, title):
		"""Display an informative (read-only) dialog for an installed controller."""
		return self._dll.MCDLG_ControllerInfo(hwnd, controller.Handle(), flags, title)

	def DownloadFile(self, hwnd, controller, flags, filename):
		"""Download a given file (typically MCCL commands and macros) to a controller."""
		return self._dll.MCDLG_DownloadFile(hwnd, controller.Handle(), flags, filename)

	def ListControllers(self, size = MC_MAX_ID + 1):
		"""Get a list of installed controllers for the user."""
		temp = (c_short * size)()
		self._dll.MCDLG_ListControllers(cast(temp, POINTER(c_short)), size)
		# convert data to a friendly python list
		controllers = []
		for i in range(0, size):
			controllers.append(temp[i])
		return controllers

	def ModuleDescEx(self, type, flags):
		"""Get a short or long text description for a particualr axis (module)."""
		buffer = create_string_buffer(256)
		self._dll.MCDLG_ModuleDescEx(type, flags, buffer, 256)
		return buffer.value.decode()

	def RestoreAxis(self, controller, axis, flags, filename):
		"""Load axis settings from a saved configuration file."""
		return self._dll.MCDLG_RestoreAxis(controller.Handle(), axis, flags, filename)

	def RestoreDigitalIO(self, controller, start, end, filename):
		"""Load digital I/O settings from a saved configuration file."""
		return self._dll.MCDLG_RestoreDigitalIO(controller.Handle(), start, end, filename)

	def SaveAxis(self, controller, axis, flags, filename):
		"""Save axis settings to a configuration file."""
		return self._dll.MCDLG_SaveAxis(controller.Handle(), axis, flags, filename)

	def SaveDigitalIO(self, controller, start, end, filename):
		"""Save digital I/O settings to a configuration file."""
		return self._dll.MCDLG_SaveDigitalIO(controller.Handle(), start, end, filename)

	def Scaling(self, hwnd, controller, axis, flags, title):
		"""Display a scale factors dialog for an axis."""
		return self._dll.MCDLG_Scaling(hwnd, controller.Handle(), axis, flags, title)

	def SelectController(self, hwnd, current_id, flags, title):
		"""Display a dialog to allow the user to select a controller from among the installed controllers."""
		return self._dll.MCDLG_SelectController(hwnd, current_id, flags, title)

	#
	# Check for errors and raise exception if needed
	#
	def ProcessException(self, error):
		if error != MCERR_NOERROR and error != MCERR_NOTSUPPORTED:
			raise McdlgException(error)
		return error

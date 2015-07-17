"""

  NAME
    pyDemo.py - a python implementation of the MCAPI's classic CWDemo demo
                program. 

  DESCRIPTION
    This program implements a windows based user  interface for a  motion 
    controller. The front panel displays position and trajectory generator 
    settings, status info, and accepts numerical move data. Setup dialogs 
    are provided for steppers, servos, scaling, controller configuration.

  RELEASE HISTORY
    Copyright (c) 2015 by Precision Micro Control Corp. All rights reserved.

    $Id: pyDemo.py 923 2015-06-23 20:14:01Z brian $

    Version 4.4.1		22-Jun-15		Programmer: R. Brian Gaynor
      - First release

"""
from tkinter import *
from math import fabs, log10 
from sys import exit
from mcapi import *
from mcdlg import *

class MyApp:
	def __init__(self, parent):
		
		self.myParent = parent 

		# local class varuiiables
		self.axis = 1							# current axis
		self.cycle = 0							# cylce mode flag
		self.id = 0								# controller ID number
		self.readout_fmt = '{0:.0f}'			# formatting for position readouts (set in OpenAxis())
		self.old_axis = 0						# so TimerUpdate can detect axis number changes
		self.ol_stepper = 0						# open/closed loop stepper flag
		self.radioModes = StringVar()			# StringVar that is bound to the move radio buttons
		self.radioModes.set("Rel")				#   default radio button mode ==> "Relative"
		self.textAxis = StringVar()				# StringVar that is bound to the distance input control
		self.textAxis.set(self.axis)			#   default distance for front panel control
		self.textDist = StringVar()				# StringVar that is bound to the distance input control
		self.textDist.set(1000)					#   default distance for front panel control

		# some layout constants
		o_padx = 6								# section frames (e.g. readout_frame) padding
		o_pady = 6
		i_padx = 4								# control frames (e.g. readout_pos) padding
		i_pady = 4
		btn_width = 9							# button settings
		btn_padx = 1
		btn_pady = 1

		# topmost frame
		self.myContainer = Frame(parent, padx=o_padx, pady=o_pady,)
		self.myContainer.pack()

		# left_frame        
		self.left_frame = Frame(self.myContainer)
		self.left_frame.pack(side=LEFT, fill=BOTH, expand=YES)

		# readouts frame (left top)
		self.readout_frame = LabelFrame(self.left_frame, padx=o_padx, pady=o_pady, height=150, width=250) 
		self.readout_frame.pack(side=TOP, fill=BOTH, expand=YES)

		# mode frame (left middle)
		self.mode_frame = LabelFrame(self.left_frame, padx=o_padx, pady=o_pady, height=75)
		self.mode_frame.pack(side=TOP, fill=BOTH, expand=YES)

		# axis frame (left bottom)
		self.axis_frame = LabelFrame(self.left_frame, padx=o_padx, pady=o_pady, height=75)
		self.axis_frame.pack(side=TOP, fill=BOTH, expand=YES)

		# center_frame 
		self.center_frame = Frame(self.myContainer)
		self.center_frame.pack(side=LEFT, fill=BOTH, expand=YES)

		# right_frame 
		self.right_frame = Frame(self.myContainer)
		self.right_frame.pack(side=LEFT, fill=BOTH, expand=YES)

		# readouts
		self.readout_pos = Frame(self.readout_frame, padx=i_padx, pady=i_pady, width=250) 
		self.readout_pos.pack(side=TOP, fill=BOTH, expand=YES)
		self.readoutPos = StringVar()
		self.MakeReadout(self.readout_pos, self.readoutPos, "Actual Position")

		self.readout_opt = Frame(self.readout_frame, padx=i_padx, pady=i_pady, width=250) 
		self.readout_opt.pack(side=TOP, fill=BOTH, expand=YES)
		self.readoutOpt = StringVar()
		self.MakeReadout(self.readout_opt, self.readoutOpt, "Optimal Position")

		self.readout_tgt = Frame(self.readout_frame, padx=i_padx, pady=i_pady, width=250) 
		self.readout_tgt.pack(side=TOP, fill=BOTH, expand=YES)
		self.readoutTgt = StringVar()
		self.MakeReadout(self.readout_tgt, self.readoutTgt, "Target Position")

		self.readout_err = Frame(self.readout_frame, padx=i_padx, pady=i_pady, width=250) 
		self.readout_err.pack(side=TOP, fill=BOTH, expand=YES)
		self.readoutErr = StringVar()
		self.MakeReadout(self.readout_err, self.readoutErr, "Following Error")

		# mode/distance
		self.text_dist = Frame(self.mode_frame, padx=i_padx, pady=i_pady, width=250) 
		self.text_dist.pack(side=TOP, fill=BOTH, expand=YES)
		Label(self.text_dist, text="Distance", width=15, justify=RIGHT).pack(side=LEFT)
		entry = Entry(self.text_dist, textvariable=self.textDist, justify=RIGHT)
		entry.pack(side=LEFT)

		self.radio_modes = Frame(self.mode_frame, padx=i_padx, pady=i_pady, width=250) 
		self.radio_modes.pack(side=TOP, fill=BOTH, expand=YES)
		Radiobutton(self.radio_modes, text="Absolute", variable=self.radioModes, value="Abs").pack(side=LEFT)
		Radiobutton(self.radio_modes, text="Relative", variable=self.radioModes, value="Rel").pack(side=LEFT)
		Radiobutton(self.radio_modes, text="Cycle", variable=self.radioModes, value="Cyc").pack(side=LEFT)

		# axis selector
		self.axis_select = Frame(self.axis_frame, padx=i_padx, pady=i_pady, width=250) 
		self.axis_select.pack(side=TOP, fill=BOTH, expand=YES)
		Label(self.axis_select, text="Axis Number", width=15, justify=RIGHT).pack(side=LEFT)
		self.axis_spinbox = Spinbox(self.axis_select, command=self.spinAxis, textvariable=self.textAxis, from_=1, to=8, justify=RIGHT, width=5)
		self.axis_spinbox.pack(side=LEFT)

		# leds
		self.led_frame1 = LabelFrame(self.center_frame, padx=o_padx, pady=o_pady, height=150, width=250) 
		self.led_frame1.pack(side=TOP)

		self.led_on = Checkbutton(self.led_frame1, text="Motor On", width=btn_width, anchor=W)
		self.led_on.pack(side=TOP)

		self.led_traj = Checkbutton(self.led_frame1, text="Traj Cmpl", width=btn_width, anchor=W)
		self.led_traj.pack(side=TOP)

		self.led_tgt = Checkbutton(self.led_frame1, text="At Target", width=btn_width, anchor=W)
		self.led_tgt.pack(side=TOP)

		self.led_dir = Checkbutton(self.led_frame1, text="Dir -", width=btn_width, anchor=W)
		self.led_dir.pack(side=TOP)

		self.led_err = Checkbutton(self.led_frame1, text="Error", width=btn_width, anchor=W)
		self.led_err.pack(side=TOP)


		self.led_frame2 = LabelFrame(self.right_frame, padx=o_padx, pady=o_pady, height=150, width=250) 
		self.led_frame2.pack(side=TOP)

		self.led_plim = Checkbutton(self.led_frame2, text="+ Limit", width=btn_width, anchor=W)
		self.led_plim.pack(side=TOP)

		self.led_mlim = Checkbutton(self.led_frame2, text="- Limit", width=btn_width, anchor=W)
		self.led_mlim.pack(side=TOP)

		self.led_home = Checkbutton(self.led_frame2, text="C. Home", width=btn_width, anchor=W)
		self.led_home.pack(side=TOP)

		self.led_idx = Checkbutton(self.led_frame2, text="Index", width=btn_width, anchor=W)
		self.led_idx.pack(side=TOP)

		self.led_flt = Checkbutton(self.led_frame2, text="Fault", width=btn_width, anchor=W)
		self.led_flt.pack(side=TOP)

		# buttons (bottom of center and right frames, 4 buttons each)
		self.button_home = Button(self.center_frame, command=self.buttonHome)
		self.button_home.configure(text="Home")
		self.button_home.configure(width=btn_width, padx=btn_padx, pady=btn_pady)
		self.button_home.pack(side=BOTTOM)    

		self.button_stop = Button(self.center_frame, command=self.buttonStop)
		self.button_stop.configure(text="Stop")
		self.button_stop.configure(width=btn_width, padx=btn_padx, pady=btn_pady)
		self.button_stop.pack(side=BOTTOM)    

		self.button_move_plus = Button(self.center_frame, command=self.buttonMovePlus)
		self.button_move_plus.configure(text="Move +")
		self.button_move_plus.configure(width=btn_width, padx=btn_padx, pady=btn_pady)
		self.button_move_plus.pack(side=BOTTOM)    

		self.button_on = Button(self.center_frame, command=self.buttonOn)
		self.button_on.configure(text="On")
		self.button_on.configure(width=btn_width, padx=btn_padx, pady=btn_pady)
		self.button_on.pack(side=BOTTOM)    

		self.button_zero = Button(self.right_frame, command=self.buttonZero)
		self.button_zero.configure(text="Zero")
		self.button_zero.configure(width=btn_width, padx=btn_padx, pady=btn_pady)
		self.button_zero.pack(side=BOTTOM)    

		self.button_abort = Button(self.right_frame, command=self.buttonStop)
		self.button_abort.configure(text="Abort")
		self.button_abort.configure(width=btn_width, padx=btn_padx, pady=btn_pady)
		self.button_abort.pack(side=BOTTOM)    

		self.button_move_minus = Button(self.right_frame, command=self.buttonMoveMinus)
		self.button_move_minus.configure(text="Move -")
		self.button_move_minus.configure(width=btn_width, padx=btn_padx, pady=btn_pady)
		self.button_move_minus.pack(side=BOTTOM)    

		self.button_off = Button(self.right_frame, command=self.buttonOff)
		self.button_off.configure(text="Off")
		self.button_off.configure(width=btn_width, padx=btn_padx, pady=btn_pady)
		self.button_off.pack(side=BOTTOM)    

		# application menu
		self.menubar = Menu(self.myParent)

		self.filemenu = Menu(self.menubar, tearoff=0)
		self.filemenu.add_command(label="Configure Axis...", command=self.menuFileConfig)
		self.filemenu.add_command(label="Scaling...", command=self.menuFileScaling)
		self.filemenu.add_separator()
		#self.filemenu.add_command(label="Always Initialize All Axes")	# we need a program INI file to support this
		self.filemenu.add_command(label="Initialize All Axes", command=self.menuFileInitAll)
		self.filemenu.add_command(label="Save All Axes Settings", command=self.menuFileSaveAll)
		self.filemenu.add_separator()
		self.filemenu.add_command(label="Controller Info...", command=self.menuFileInfo)
		self.filemenu.add_command(label="Select Controller...", command=self.menuFileSelect)
		self.filemenu.add_command(label="Reset Controller")
		self.filemenu.add_separator()
		self.filemenu.add_command(label="Exit", command=self.myParent.quit)
		self.menubar.add_cascade(label="Setup", menu=self.filemenu)

		self.helpmenu = Menu(self.menubar, tearoff=0)
		self.helpmenu.add_command(label="About", command=self.menuHelpAbout)
		self.menubar.add_cascade(label="Help", menu=self.helpmenu)

		self.myParent.config(menu=self.menubar)

		# controller
		self.ctlr = Mcapi()						# create a MCAPI controller object
		self.dlgs = Mcdlg()						# motion dialogs for axis setup, scaling, etc.

		# open and configure a controller
		while True:
			if self.OpenController() > 0:
				break
			else:
				self.id = mcdlg.SelectController(self.myContainer.winfo_id(), -1, 0, None)
				if self.id >= 0:
					continue
				exit(1)

		# start the update timer
		self.TimerUpdate()

	def TimerUpdate(self):
		if self.axis != self.old_axis:
			self.old_axis = self.axis
			self.OpenAxis()

		status = self.ctlr.GetStatus(self.axis)
		self.old_status = status

		#buttons
		motor_on = self.ctlr.DecodeStatus(status, MC_STAT_MTR_ENABLE)
		motor_err = self.ctlr.DecodeStatus(status, MC_STAT_ERROR)
		if motor_on != 0:
			self.button_off.config(state=NORMAL)
		else:
			self.button_off.config(state=DISABLED)
		if motor_on != 0 and motor_err == 0:
			self.button_move_plus.config(state=NORMAL)
			self.button_move_minus.config(state=NORMAL)
			self.button_stop.config(state=NORMAL)
			self.button_abort.config(state=NORMAL)
			self.button_home.config(state=NORMAL)
		else:
			self.button_move_plus.config(state=DISABLED)
			self.button_move_minus.config(state=DISABLED)
			self.button_stop.config(state=DISABLED)
			self.button_abort.config(state=DISABLED)
			self.button_home.config(state=DISABLED)

		# leds
		if self.ctlr.DecodeStatus(status, MC_STAT_MTR_ENABLE):
			self.led_on.config(selectcolor="limegreen")
		else:
			self.led_on.config(selectcolor="black")

		if self.ctlr.DecodeStatus(status, MC_STAT_TRAJ):
			self.led_traj.config(selectcolor="limegreen")
		else:
			self.led_traj.config(selectcolor="black")

		if self.ctlr.DecodeStatus(status, MC_STAT_AT_TARGET):
			self.led_tgt.config(selectcolor="limegreen")
		else:
			self.led_tgt.config(selectcolor="black")

		if self.ctlr.DecodeStatus(status, MC_STAT_DIR):
			self.led_dir.config(selectcolor="yellow")
		else:
			self.led_dir.config(selectcolor="black")

		if self.ctlr.DecodeStatus(status, MC_STAT_ERROR):
			self.led_err.config(selectcolor="red")
		else:
			self.led_err.config(selectcolor="black")

		if self.ctlr.DecodeStatus(status, MC_STAT_PLIM_TRIP):
			self.led_plim.config(selectcolor="red")
		else:
			self.led_plim.config(selectcolor="black")

		if self.ctlr.DecodeStatus(status, MC_STAT_MLIM_TRIP):
			self.led_mlim.config(selectcolor="red")
		else:
			self.led_mlim.config(selectcolor="black")

		if self.ctlr.DecodeStatus(status, MC_STAT_INP_HOME):
			self.led_home.config(selectcolor="yellow")
		else:
			self.led_home.config(selectcolor="black")

		if self.ctlr.DecodeStatus(status, MC_STAT_INP_INDEX):
			self.led_idx.config(selectcolor="yellow")
		else:
			self.led_idx.config(selectcolor="black")

		if self.ctlr.DecodeStatus(status, MC_STAT_AMP_FAULT):
			self.led_flt.config(selectcolor="red")
		else:
			self.led_flt.config(selectcolor="black")

		# readouts
		val = self.ctlr.GetPositionEx(self.axis)
		self.readoutPos.set(self.readout_fmt.format(val))
		val = self.ctlr.GetOptimalEx(self.axis)
		self.readoutOpt.set(self.readout_fmt.format(val))
		val = self.ctlr.GetTargetEx(self.axis)
		self.readoutTgt.set(self.readout_fmt.format(val))
		# don't display following error on open loop steppers
		if self.ol_stepper == 0:
			val = self.ctlr.GetFollowingError(self.axis)
			self.readoutErr.set(self.readout_fmt.format(val))
		else:
			self.readoutErr.set(" ")

		# cycle mode
		if motor_on != 0 and motor_err == MCERR_NOERROR:
			if self.cycle != 0 and self.ctlr.IsStopped(self.axis, 0):
				if self.cycle == 1:
					self.buttonMoveMinus()
				else:
					self.buttonMovePlus()
		else:
			self.cycle = 0

		self.myParent.after(100, self.TimerUpdate)

	def menuFileConfig(self):
		self.dlgs.ConfigureAxis(self.myContainer.winfo_id(), self.ctlr, self.axis, MCDLG_PROMPT | MCDLG_CHECKACTIVE, None)
		self.cycle = 0

	def menuFileScaling(self):
		self.dlgs.Scaling(self.myContainer.winfo_id(), self.ctlr, self.axis, MCDLG_PROMPT | MCDLG_CHECKACTIVE, None)
		self.cycle = 0

	def menuFileInitAll(self):
		self.dlgs.RestoreAxis(self.ctlr, MC_ALL_AXES, MCDLG_PROMPT | MCDLG_CHECKACTIVE, None)
		self.cycle = 0

	def menuFileSaveAll(self):
		self.dlgs.SaveAxis(self.ctlr, MC_ALL_AXES, MCDLG_PROMPT | MCDLG_CHECKACTIVE, None)
		self.cycle = 0

	def menuFileInfo(self):
		self.dlgs.ControllerInfo(self.myContainer.winfo_id(), self.ctlr, 0, None)
		self.cycle = 0

	def menuFileSelect(self):
		while True:
			self.id = self.dlgs.SelectController(self.myContainer.winfo_id(), self.id, 0, None)
			if self.OpenController() > 0:
				break
			elif self.id >= 0:
				continue
			exit(1)
		self.cycle = 0

	def menuHelpAbout(self): 
		self.dlgs.AboutBox(self.myContainer.winfo_id(), None, 0)
		self.cycle = 0

	def buttonOn(self): 
		self.ctlr.EnableAxis(self.axis, 1)
		self.old_axis = 0					# force recalculation of display precision
		self.cycle = 0

	def buttonMovePlus(self): 
		if self.radioModes.get() == "Abs":
			self.ctlr.MoveAbsolute(self.axis, float(self.textDist.get()))
		else:
			self.ctlr.MoveRelative(self.axis, float(self.textDist.get()))
			if self.radioModes.get() == "Cyc":	# cycle mode
				self.cycle = 1

	def buttonMoveMinus(self): 
		if self.radioModes.get() == "Abs":
			self.ctlr.MoveAbsolute(self.axis, float(self.textDist.get()) * -1)
		else:
			self.ctlr.MoveRelative(self.axis, float(self.textDist.get()) * -1)
			if self.radioModes.get() == "Cyc":	# cycle mode
				self.cycle = -1

	def buttonStop(self): 
		self.ctlr.Stop(self.axis)
		self.cycle = 0

	def buttonHome(self): 
		self.ctlr.GoHome(self.axis)
		self.cycle = 0

	def buttonOff(self): 
		self.ctlr.EnableAxis(self.axis, 0)
		self.cycle = 0

	def buttonAbort(self): 
		self.ctlr.Abort(self.axis)
		self.cycle = 0

	def buttonZero(self): 
		self.ctlr.SetPosition(self.axis, 0)
		self.cycle = 0

	def spinAxis(self): 
		self.axis = int(self.textAxis.get())
		self.cycle = 0

	def OnClose(self):
		self.ctlr.Close()
		root.destroy()

	def OpenAxis(self):
		axis_config = MCAXISCONFIG()
		self.ctlr.GetAxisConfiguration(self.axis, axis_config)
		if axis_config.MotorType & MC_TYPE_SERVO:
			self.led_idx.config(text="Index")
			self.ol_stepper = 0
		else:
			self.led_idx.config(text="Home")
			if self.ctlr.GetModuleInputMode(self.axis) == MC_IM_OPENLOOP:
				self.ol_stepper = 1
			else:
				self.ol_stepper = 0

		if self.ctlr.GetOperatingMode(self.axis) != MC_MODE_POSITION:
			self.ctlr.SetOperatingMode(self.axis, 0, MC_MODE_POSITION)

		# look at axis scaling to determine number of decimal places to display
		scaling = MCSCALE()
		self.ctlr.GetScale(self.axis, scaling)
		n = int(log10(fabs(scaling.Scale)) + 0.99)
		self.readout_fmt = '{{0:.{0!s}f}}'.format(n)

	def OpenController(self):
		self.ctlr.Open(self.id, MC_OPEN_BINARY)

		if self.ctlr._handle <= 0:
			messagebox.showerror("Open Controller", "Unable to open controller #" + id + ", error: " + ctlr.TranslateError(self.ctlr._handle))
			return self.ctlr._handle

		param = MCPARAMEX()
		self.ctlr.GetConfigurationEx(param)
		if param.NumberAxes == 0:
			messagebox.showerror("No Axes", "No motor axes are installed on this controller. pyDemo requires at least one servo or stepper axes.")
			self.ctlr.Close()
			return 0

		# Initialize the axes
		#if (GetMenuState(GetMenu(hWnd), IDM_AUTO_INIT, MF_BYCOMMAND) & MF_CHECKED)
		#	MCDLG_RestoreAxis(hCtlr, MC_ALL_AXES, MCDLG_PROMPT | MCDLG_CHECKACTIVE, NULL);

		if self.axis > param.NumberAxes:
			self.axis = 1

		self.axis_spinbox.delete(0, last=END)
		for axis in range(1, param.NumberAxes + 1):
			self.axis_spinbox.insert(END, str(axis))
		self.textAxis.set(self.axis)

		return self.ctlr._handle

	def MakeReadout(self, parent, bind, caption):
		Label(parent, text=caption, width=13, justify=RIGHT).pack(side=LEFT)
		entry = Entry(parent, textvariable=bind, width=15, background="black", foreground="lime", justify=RIGHT, font="System 12 bold")
		entry.pack(side=LEFT)
		return entry

root = Tk()
root.title("pyDemo")
root.iconbitmap('pyDemo.ico')
myapp = MyApp(root)
root.protocol("WM_DELETE_WINDOW", myapp.OnClose)
root.mainloop()

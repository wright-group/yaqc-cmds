### import ####################################################################


import os
import collections
import time

import numpy as np

from PyQt4 import QtGui, QtCore

import wx
from wx.lib.pubsub import Publisher
import wx.lib.activex

import comtypes.client as cc
cc.GetModule(('{2A833923-9AA7-4C45-90AC-DA4F19DC24D1}', 1, 0))
progID_motor = 'MGMOTOR.MGMotorCtrl.1'
from ctypes import byref, pointer, c_long, c_float, c_bool
import comtypes.gen.MG17MotorLib as APTMotorLib

import project.classes as pc
import project.widgets as pw
import project.project_globals as g
from project.ini_handler import Ini
main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'delays',
                                 'LTS300',
                                 'LTS300.ini'))


### define ####################################################################


channel1 = APTMotorLib.CHAN1_ID
channel2 = APTMotorLib.CHAN2_ID
break_type_switch = APTMotorLib.HWLIMSW_BREAKS
units_mm = APTMotorLib.UNITS_MM
home_rev = APTMotorLib.HOME_REV
homelimsw_rev = APTMotorLib.HOMELIMSW_REV_HW

motor_moving_bits =  -2147478512
motor_stopped_not_homed_bits = -2147479552
motor_stopped_and_homed_bits = -2147478528

ps_per_mm = 6.671281903963041  # a mm on the delay stage (factor of 2)


### active x control ##########################################################

#see http://people.seas.harvard.edu/~krussell/html-pyPL/APTMotorControl.html

#for future reference: http://stackoverflow.com/questions/25374622/cannot-pass-arguments-to-activex-com-object-using-pyqt4


class APTMotor(wx.lib.activex.ActiveXCtrl):
    """The Motor class derives from wx.lib.activex.ActiveXCtrl, which
       is where all the heavy lifting with COM gets done."""
    
    def __init__(self, 
                 parent, 
                 HWSerialNum, 
                 id=wx.ID_ANY, 
                 pos=wx.DefaultPosition,
                 size=wx.DefaultSize, 
                 style=0, 
                 name='Stepper Motor'):
                     
        wx.lib.activex.ActiveXCtrl.__init__(self, parent, progID_motor, id, pos, size, style, name)
                                            
        self.ctrl.HWSerialNum = HWSerialNum
        self.ctrl.StartCtrl()
        self.ctrl.EnableHWChannel( channel1 )
        
        """ Global variables:"""
        self.StepSize = 0.05 # initial step size (mm)
        self.PositionCh1 = 0.0
        self.PositionCh2 = 0.0     
        
    def GetPosition( self, channel=channel1 ):
        position = c_float()
        self.ctrl.GetPosition(channel, byref(position))
        if channel==channel1: self.PositionCh1 = position.value
        return position.value
        
    def MoveAbsoluteEx(self, position_ch1=0.0, position_ch2=0.0, channel=channel1, wait=True):
        """
        Move motor to a specified position.

        *position_ch1*
            target position (in mm) of channel 1 (the default channel)
        
        *position_ch2*
            target position (in mm) of channel 2. I'm not sure what it
            means to have different channels...
        
        *channel*
            the channel you want to move. I always use default (channel1).
        
        *wait*
            Wait for the motor to finish moving? Default is True.

        """
        if ( channel==channel1 and 
                position_ch1 > self.GetStageAxisInfo_MinPos(channel) and
                position_ch1 < self.GetStageAxisInfo_MaxPos(channel) ): 
            self.PositionCh1 = position_ch1
            return self.ctrl.MoveAbsoluteEx( channel, position_ch1, position_ch2, wait )
            
    def MoveHome(self, channel=channel1 , wait=True ):
        return self.ctrl.MoveHome( channel, wait )
            
    def GetStageAxisInfo_MinPos( self, channel=channel1 ):
        """Get the minimum position of the stage that is accessible using
            the MoveAbsoluteEx or MoveRelativeEx commands, although you
            may be able to exceed it by Jogging. I think this is a
            user-settable quantity. For the small stepper we have, if
            it's been "homed" then it sets 0 to be the minimum position."""
        return self.ctrl.GetStageAxisInfo_MinPos( channel )
        
    def GetStageAxisInfo_MaxPos( self, channel=channel1 ):
        """Get the maximum position of the stage that is accessible using
            the MoveAbsoluteEx or MoveRelativeEx commands, although you
            may be able to exceed it by Jogging. I think this is a
            user-settable quantity. For the small stepper we have,
            the max travel is like 18mm. (Or should be ~25mm?) """
        return self.ctrl.GetStageAxisInfo_MaxPos( channel )
        
    def SetStepSize( self, stepsize ):
        """
        Set the step size for the StepUp and StepDown methods.

        *stepsize*
            step size in mm.
        """
        self.StepSize = stepsize
        
    def StopImmediate( self, channel=channel1 ):
        """ Stops the motor from moving (although this won't overcome the strange ActiveX
        phantom-motor-moving issue where the control says it is moving but actually isn't. """
        return self.ctrl.StopImmediate( channel )
        
    def SetBLashDist( self, channel=channel1, backlash=0.01 ):
        """
        Sets the backlash distance in mm.

        *channel*
           channel1 by default

        *backlash*
           distance in mm, 0.01 by default
         """
        return self.ctrl.SetBLashDist( channel, backlash )
        
    def GetStatusBits_Bits( self, channel=channel1 ):
        """ Returns the status bits. """
        return self.ctrl.GetStatusBits_Bits( channel )

    def MotorIsNotMoving( self, channel=channel1 ):
        """
        checks if the status bits of the motor indicate that the motor is stopped
        """
        return self.GetStatusBits_Bits( channel ) in [ motor_stopped_not_homed_bits, motor_stopped_and_homed_bits]
    
    def SetStageAxisInfo( self, channel=channel1, minpos=0.0, maxpos=12.0, pitch=1.0, units=units_mm ):
        """
        Set the stage axis info.

        *channel*
            channel1 by default

        *minpos*
            0.0 (mm) by default

        *maxpos*
            12.0 (mm) by default

        *pitch*
            1.0 by default

        *units*
            units_mm by default

        """
        return self.ctrl.SetStageAxisInfo( channel, minpos, maxpos, units, pitch, 1 )
        

### driver ####################################################################


class app(wx.App):
    
    def __init__(self):
        wx.App.__init__(self, redirect=False)
        self.native_units = 'ps'
        # mutex attributes
        self.limits = pc.NumberLimits(units=self.native_units)
        self.motor_limits = pc.NumberLimits(min_value=0, max_value=300, units='mm')
        self.current_position = pc.Number(name='Delay', initial_value=0.,
                                          limits=self.limits,
                                          units=self.native_units, 
                                          display=True,
                                          set_method='set_position')
        self.offset = pc.Number(initial_value=0, 
                                units=self.native_units, display=True)
        self.current_position_mm = pc.Number(units='mm', display=True, decimals=3,
                                             limits=self.motor_limits)
        # objects to be sent to PyCMDS
        self.exposed = [self.current_position]
        self.recorded = collections.OrderedDict()
        # finish
        self.gui = GUI(self)
        self.initialized = pc.Bool()
        
    def close(self):
        pass
    
    def get_position(self):
        # read (mm)
        position = self.motor_control.GetPosition()
        self.current_position_mm.write(position, 'mm')
        # calculate delay (fs)
        delay = (position - self.zero_position.read()) * ps_per_mm
        self.current_position.write(delay, 'ps')
        return delay
        
    def home(self, inputs=[]):
        # move hardware
        self.motor_control.MoveHome(wait=False)
        while not self.motor_control.MotorIsNotMoving():
            time.sleep(0.01)
            self.get_position()
        # get position
        self.get_position()
        
    def initialize(self, inputs, address):
        self.address = address
        # create dummy frame
        self.frame_aptcontrols = wx.Frame( None, wx.ID_ANY, title='pyPL -- APT Controls', size=wx.Size(1400,220) )
        self.panel_aptcontrols = wx.Panel( self.frame_aptcontrols, wx.ID_ANY )     
        self.initframe = wx.Frame( self.frame_aptcontrols, wx.ID_ANY, title='pyPosition is initializing...', size=wx.Size(550, 70) )
        self.initpanel = wx.Panel( self.initframe, wx.ID_ANY )
        self.hsizer = wx.BoxSizer( wx.HORIZONTAL )
        self.inittext = wx.StaticText( self.initpanel, label='Initializing piezos & motors, takes a few seconds... MAKE SURE ALL ARE HOMED/ZEROED!')
        self.hsizer.Add( self.inittext, flag=wx.ALL|wx.CENTER, border=3 )
        self.button_HideInitWindow = wx.Button( self.initpanel, wx.ID_ANY, 'Dismiss' )
        self.hsizer.Add( self.button_HideInitWindow, flag=wx.ALL|wx.CENTER, border=3 )
        self.initpanel.SetSizer( self.hsizer )
        self.initframe.Center()
        # load motor_control
        motor_serial_number = ini.read('main', 'serial number')
        self.motor_control = APTMotor(self.frame_aptcontrols, motor_serial_number)
        # read zero position from ini
        self.zero_position = pc.Number(name='Zero', initial_value=12.5,
                                       ini=ini, section='main', option='zero position (mm)',
                                       import_from_ini=True,
                                       save_to_ini_at_shutdown=True,
                                       limits=self.motor_limits,
                                       decimals=3,
                                       units='mm', display=True)
        self.set_zero(self.zero_position.read())
        # recorded
        self.recorded['d0'] = [self.current_position, self.native_units, 1., '0', False]
        self.recorded['d0_zero'] = [self.zero_position, 'mm', 1., '0', False]
        # finish
        self.get_position()
        self.initialized.write(True)
        self.address.initialized_signal.emit()
    
    def is_busy(self):
        return not self.motor_control.MotorIsNotMoving()
        
    def set_offset(self, offset):
        # update zero
        offset_from_here = offset - self.offset.read('fs')
        offset_mm = offset_from_here/ps_per_mm
        new_zero = self.zero_position.read('mm') + offset_mm
        self.set_zero(new_zero)
        self.offset.write(offset)
        # return to old position
        destination = self.address.hardware.destination.read('fs')
        self.set_position(destination)
    
    def set_position(self, destination):
        # get destination_mm
        destination_mm = self.zero_position.read() + destination/ps_per_mm
        self.set_position_mm([destination_mm])
        
    def set_position_mm(self, inputs):
        destination = inputs[0]
        # move hardware
        self.motor_control.MoveAbsoluteEx(position_ch1=destination, wait=False)
        while not self.motor_control.MotorIsNotMoving():
            time.sleep(0.01)
            self.get_position()
        # get position
        self.get_position()
    
    def set_zero(self, zero):
        self.zero_position.write(zero)
        min_value = -self.zero_position.read() * ps_per_mm
        max_value = (300. - self.zero_position.read()) * ps_per_mm
        self.limits.write(min_value, max_value, 'ps')
        # write new position to ini
        section = 'main'
        option = 'zero position (mm)'
        ini.write(section, option, zero)
        # get new position
        self.get_position()

class app_offline(app):
    
    def initialize(self, inputs, address):
        pass


### gui #######################################################################


class GUI(QtCore.QObject):

    def __init__(self, driver):
        QtCore.QObject.__init__(self)
        self.driver = driver

    def create_frame(self, layout):
        layout.setMargin(5)
        self.layout = layout
        self.frame = QtGui.QWidget()
        self.frame.setLayout(self.layout)
        g.module_advanced_widget.add_child(self.frame)
        if self.driver.initialized.read():
            self.initialize()
        else:
            self.driver.initialized.updated.connect(self.initialize)

    def initialize(self):
        # settings container
        settings_container_widget = QtGui.QWidget()
        settings_scroll_area = pw.scroll_area(show_bar=False)
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        self.layout.addWidget(settings_scroll_area)
        # mm input table
        input_table = pw.InputTable()
        input_table.add('Position', None)
        input_table.add('Current', self.driver.current_position_mm)
        self.mm_destination = self.driver.current_position_mm.associate(display=False)
        input_table.add('Destination', self.mm_destination)
        settings_layout.addWidget(input_table)
        # set mm button
        self.set_mm_button = pw.SetButton('SET POSITION')
        settings_layout.addWidget(self.set_mm_button)
        self.set_mm_button.clicked.connect(self.on_set_mm)
        g.module_control.disable_when_true(self.set_mm_button)
        # zero input table
        input_table = pw.InputTable()
        input_table.add('Zero', None)
        input_table.add('Current', self.driver.zero_position)
        self.zero_destination = self.driver.zero_position.associate(display=False)
        input_table.add('Destination', self.zero_destination)
        settings_layout.addWidget(input_table)
        # set zero button
        self.set_zero_button = pw.SetButton('SET ZERO')
        settings_layout.addWidget(self.set_zero_button)
        self.set_zero_button.clicked.connect(self.on_set_zero)
        g.module_control.disable_when_true(self.set_zero_button)
        # horizontal line
        settings_layout.addWidget(pw.line('H'))
        # home button
        input_table = pw.InputTable()
        self.home_button = pw.SetButton('HOME')
        settings_layout.addWidget(self.home_button)
        self.home_button.clicked.connect(self.on_home)
        g.module_control.disable_when_true(self.home_button)
        # finish
        settings_layout.addStretch(1)
        self.layout.addStretch(1)
        self.driver.address.update_ui.connect(self.update)
        
    def on_home(self):
        self.driver.address.hardware.q.push('home')
        
    def on_set_mm(self):
        new_mm = self.mm_destination.read('mm')
        new_mm = np.clip(new_mm, 1e-3, 300-1e-3)
        self.driver.address.hardware.q.push('set_position_mm', [new_mm])
        
    def on_set_zero(self):
        new_zero = self.zero_destination.read('mm')
        self.driver.set_zero(new_zero)
        self.driver.offset.write(0)
        name = self.driver.address.hardware.name
        g.coset_control.read().zero(name)

    def update(self):
        pass

    def stop(self):
        pass


### testing ###################################################################


if __name__ == '__main__':
    
    control = app()
    control.initialize()

    print 'test'

    print control.get_position()
    
    control.move_absolute(10)

    control.move_absolute(30)

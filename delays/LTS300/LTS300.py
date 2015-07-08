### import #####################################################################

import wx
from wx.lib.pubsub import Publisher
import wx.lib.activex
import comtypes.client as cc
cc.GetModule(('{2A833923-9AA7-4C45-90AC-DA4F19DC24D1}', 1, 0))
progID_motor = 'MGMOTOR.MGMotorCtrl.1'
from ctypes import byref, pointer, c_long, c_float, c_bool
import comtypes.gen.MG17MotorLib as APTMotorLib

### define #####################################################################

channel1 = APTMotorLib.CHAN1_ID
channel2 = APTMotorLib.CHAN2_ID
break_type_switch = APTMotorLib.HWLIMSW_BREAKS
units_mm = APTMotorLib.UNITS_MM
home_rev = APTMotorLib.HOME_REV
homelimsw_rev = APTMotorLib.HOMELIMSW_REV_HW

motor_moving_bits =  -2147478512
motor_stopped_not_homed_bits = -2147479552
motor_stopped_and_homed_bits = -2147478528

### address motor ##############################################################
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
        
### control address object #####################################################

class control(wx.App):
    
    def __init__(self):
        wx.App.__init__(self, redirect=False)
        
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
        
        self.motor_control = APTMotor(self.frame_aptcontrols, 45837036)
        
    def move_absolute(self, destination):
        '''
        tell the motor to start moving towards the destination, in mm
        '''
        self.motor_control.MoveAbsoluteEx(position_ch1 = destination, wait = True)
        
    def get_current_position(self):
        '''
        returns the current position of the motor in mm
        '''
        return self.motor_control.GetPosition()

control = control()
print control.get_current_position(), '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'

### testing ####################################################################

if __name__ == '__main__':
    import os 
    os.chdir('C:\Users\John\Desktop\PyCMDS')

    print 'test'

    print control.get_current_position()
    
    control.move_absolute(10)

    control.move_absolute(30)
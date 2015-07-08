#http://stackoverflow.com/questions/25374622/cannot-pass-arguments-to-activex-com-object-using-pyqt4

### import #####################################################################

import sys
from ctypes import *

import comtypes.gen.MG17MotorLib as APTMotorLib
import comtypes.client as cc

from PyQt4 import QtGui
from PyQt4 import QAxContainer
from PyQt4.QtCore import QVariant

### define #####################################################################

channel1 = APTMotorLib.CHAN1_ID
channel2 = APTMotorLib.CHAN2_ID
break_type_switch = APTMotorLib.HWLIMSW_BREAKS
units_mm = APTMotorLib.UNITS_MM
home_rev = APTMotorLib.HOME_REV
homelimsw_rev = APTMotorLib.HOMELIMSW_REV_HW

cc.GetModule(('{2A833923-9AA7-4C45-90AC-DA4F19DC24D1}', 1, 0))
ProgID = '{B74DB4BA-8C1E-4570-906E-FF65698D632E}'
ProgID_motor = 'MGMOTOR.MGMotorCtrl.1'
hw_serial_num = 45837036

### ActiveX container ##########################################################

class APTMotor(QAxContainer.QAxWidget):
    '''
    use the generateDocumentation method on an APTMotor to get all avalible
    activex methods
    '''
    def __init__(self, parent):
        self.parent = parent
        self.channel = channel1
        super(APTMotor, self).__init__()
        self.setControl(ProgID_motor)
        self.SetHWSerialNum(hw_serial_num)
        self.StartCtrl()
        self.EnableHWChannel(self.channel)
    def get_brake_state(self):
        state = c_uint()
        self.GetBrakeState(self.channel, pointer(state))
        return state.value
    def get_position(self):
        '''
        returns [position (mm)]
        '''
        position = self.GetPosition_Position(self.channel)        
        return [position]
    def get_stage_axis_info(self):
        '''
        returns [float min_position (mm), float max_position (mm)]
        '''
        _min = self.GetStageAxisInfo_MinPos(self.channel)
        _max = self.GetStageAxisInfo_MaxPos(self.channel)
        return [_min, _max]
    def move_home(self, wait = True):
        '''
        bool wait
        returns [error]
        '''
        error = self.MoveHome(self.channel, wait)
        return [error]
    def motor_is_not_moving(self):
        """
        returns [bool state]
        """
        motor_moving_bits            = -2147478512
        motor_stopped_not_homed_bits = -2147479552
        motor_stopped_and_homed_bits = -2147478528
        state = self.GetStatusBits_Bits(self.channel) in [motor_stopped_not_homed_bits, motor_stopped_and_homed_bits]
        return [state]
    def move_absolute(self, destination, wait = True):
        '''
        float destination (mm), bool wait
        returns [error]
        '''
        print 'dest', destination
        error = self.MoveAbsoluteEx(self.channel, 10.0, 10.0, wait)
        return [error]
    def shut_down(self):
        '''
        returns [channel disable error, stop control error]
        '''
        channel_error = self.DisableHWChannel(self.channel)
        control_error = self.StopCtrl()
        return [channel_error, control_error]
        
### testing ####################################################################

app = QtGui.QApplication(sys.argv) 

if __name__ == '__main__':
               
    motor = APTMotor(app)
    
    
    #print motor.get_stage_axis_info()channel, minpos, maxpos, units, pitch, 1
    #motor.SetStageAxisInfo(channel1, 0., 300., units_mm, 1., 1.)
    print motor.get_position()
    #motor.c
    #print motor.move_home()
    print motor.move_absolute(10.)
    #print motor.move_absolute(30)
    #print motor.motor_is_not_moving()
    
    #print motor.shut_down()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
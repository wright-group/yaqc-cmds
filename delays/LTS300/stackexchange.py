import sys

import comtypes.gen.MG17MotorLib as APTMotorLib

from PyQt4 import QtGui
from PyQt4 import QAxContainer

channel1 = APTMotorLib.CHAN1_ID

class APTMotor(QAxContainer.QAxWidget):
    def __init__(self, parent):
        self.parent = parent
        super(APTMotor, self).__init__()
        self.setControl('MGMOTOR.MGMotorCtrl.1')
        #motor specific initialization 
        self.SetHWSerialNum(45837036)
        self.StartCtrl()
        self.EnableHWChannel(channel1)

app = QtGui.QApplication(sys.argv) 
motor = APTMotor(app)

print motor.GetStageAxisInfo_MinPos(channel1)
print motor.GetStageAxisInfo_MaxPos(channel1)
print motor.GetPosition_Position(channel1)
print motor.MoveAbsoluteEx(channel1, 10., 0., True)


#shut down motor
print motor.DisableHWChannel(channel1)
print motor.StopCtrl()
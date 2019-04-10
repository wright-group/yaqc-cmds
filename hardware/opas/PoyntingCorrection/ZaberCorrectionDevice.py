### import ####################################################################


import time

import library.zaber.binary as zb
import project.classes as pc
from hardware.opas.PoyntingCorrection.PoyntingCorrectionDevice import PoyntingCorrectionDevice


### define ####################################################################


### driver ####################################################################


class ZaberCorrectionDevice(PoyntingCorrectionDevice):
    
    def __init__ (self, port, indexes, native_units = 'wn'):
        self.portStg = str(port)
        self.indexes = list(indexes[0])
        PoyntingCorrectionDevice.__init__(self, native_units)

    def _get_motor_position(self, index):
        return self.motors[index].get_position()

    def _home(self, index):
        position = self.motors[index].get_position()
        self.motors[index].home()
        self.motors[index].move_abs(position)
    
    def _initialize(self):
        self.port = zb.BinarySerial(self.portStg)
        for i in self.indexes:
            self.motors.append(zb.BinaryDevice(self.port, i))    

    def _set_motor(self, index, position):
        return self.motors[index].move_abs(position)
  
    def _zero(self, index):
        self.motors[index].home()
        time.sleep(2)
        self.motors[index].move_abs(0)
  
    def motor_limits(self):
        return pc.NumberLimits(min_value=-62000, max_value=62000)
        
    def is_busy(self):
        return False
        busy = False
        for motor in self.motors:
            busy = busy or motor.get_status() != 0
        return busy

    def close(self):
        self.port.close()

import project.zaber.binary as zb
import project.classes as pc
from hardware.opas.PoyntingCorrection.PoyntingCorrectionDevice import PoyntingCorrectionDevice

import time

class ZaberCorrectionDevice(PoyntingCorrectionDevice):
    def motor_limits(self):
        return pc.NumberLimits(min_value = -62000, max_value = 62000)
    def _initialize(self,inputs):
        portStg = self.ini.read('OPA%d'%self.index, 'port')
        self.port = zb.BinarySerial(portStg)

        indexes = self.ini.read('OPA%d'%self.index, 'zaber_device_numbers')

        for i in indexes:
            self.motors.append(zb.BinaryDevice(self.port, i))

    def is_busy(self):
        return False
        busy = False
        for motor in self.motors:
            busy = busy or motor.get_status() != 0
        return busy

    def _home(self, index):
        position = self.motors[i].get_position()
        self.motors[i].home()
        time.sleep(2)
        self.motors[i].move_abs(position)

    def _zero(self, index):
        self.motors[i].home()
        time.sleep(2)
        self.motors[i].move_abs(0)

    def _get_motor_position(self, index):
        return self.motors[i].get_position()
    def _set_motor(self, index, position):
        return self.motors[index].move_abs(position)
    def close(self):
        self.port.close()

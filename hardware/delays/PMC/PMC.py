### import ####################################################################
import time

import project.classes as pc
import project.project_globals as g
from hardware.delays.delays import Driver as BaseDriver
from hardware.delays.delays import GUI as BaseGUI
#import library.precision_micro_motors.precision_motors as motors
import yaqc


### define ####################################################################


main_dir = g.main_dir.read()


### driver ####################################################################


class Driver(BaseDriver):

    def __init__(self, *args, **kwargs):
        BaseDriver.__init__(self, *args, **kwargs)
        self.index = kwargs['index']
        self.yaqd_port = kwargs["yaqd_port"]
        self.native_per_mm = 6.671281903963041

    def close(self):
        self.motor.close()

    def get_position(self):
        position = self.motor.get_position()
        self.motor_position.write(position, 'mm')
        delay = (position - self.zero_position.read()) * self.native_per_mm * self.factor.read()
        self.position.write(delay, 'ps')
        return delay

    def initialize(self):
        self.motor = yaqc.Client(self.yaqd_port)
        self.current_position_mm = pc.Number(units='mm', display=True, decimals=5)
        # finish
        self.get_position()
        self.initialized.write(True)
        self.initialized_signal.emit()

    def is_busy(self):
        self.busy.write(self.motor.busy())
        return self.busy.read()

    def set_position(self, destination):
        destination_mm = self.zero_position.read() + destination/(self.native_per_mm * self.factor.read())
        self.set_motor_position(destination_mm)
    
    def set_motor_position(self, destination):
        self.motor.set_position(destination)
        time.sleep(0.01)
        while self.is_busy():
            self.get_position()
        self.get_position()

    def set_zero(self, zero):
        self.zero_position.write(zero)
        min_value = -self.zero_position.read() * self.native_per_mm * self.factor.read()
        max_value = (50. - self.zero_position.read()) * self.native_per_mm * self.factor.read()
        self.limits.write(min_value, max_value, 'ps')
        self.get_position()


### gui #######################################################################


class GUI(BaseGUI):
    pass

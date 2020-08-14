# --- import --------------------------------------------------------------------------------------


import time

import pycmds.project.project_globals as g
from hardware.delays.delays import Driver as BaseDriver
from hardware.delays.delays import GUI as BaseGUI

from library.ThorlabsAPT.APT import APTMotor


# --- define --------------------------------------------------------------------------------------


main_dir = g.main_dir.read()


# --- driver --------------------------------------------------------------------------------------


class Driver(BaseDriver):
    def __init__(self, *args, **kwargs):
        BaseDriver.__init__(self, *args, **kwargs)
        kwargs["native_units"] = "ps"
        self.index = kwargs.pop("index")
        self.native_per_mm = 6.671281903963041

    def close(self):
        self.motor.close()

    def get_motor_position(self):
        p = self.motor.position
        self.motor_position.write(p, self.motor_units)
        return p

    def get_position(self):
        position = self.get_motor_position()
        # calculate delay
        delay = (position - self.zero_position.read()) * self.native_per_mm * self.factor.read()
        self.position.write(delay, self.native_units)
        # return
        return delay

    def home(self):
        self.motor.go_home()
        self.set_position(self.hardware.destination.read())

    def initialize(self):
        self.motor = APTMotor(serial_number=int(self.serial), hardware_type=42)
        self.motor_limits.write(
            self.motor.minimum_position, self.motor.maximum_position, self.motor_units
        )
        self.update_recorded()
        self.set_zero(self.zero_position.read())
        self.get_position()
        self.initialized.write(True)
        self.initialized_signal.emit()

    def is_busy(self):
        return not "stopped" in self.motor.status

    def set_position(self, destination):
        destination_mm = self.zero_position.read() + destination / (
            self.native_per_mm * self.factor.read()
        )
        self.set_motor_position(destination_mm)

    def set_motor_position(self, motor_position):
        self.motor.set_position(motor_position)
        while self.is_busy():
            time.sleep(0.01)
            self.get_position()
        # do it again (see issue #78)
        time.sleep(0.05)
        while self.is_busy():
            time.sleep(0.01)
            self.get_position()
        self.get_position()
        BaseDriver.set_motor_position(self, motor_position)

    def set_zero(self, zero):
        self.zero_position.write(zero)
        min_value = -self.zero_position.read() * self.native_per_mm * self.factor.read()
        max_value = (300.0 - self.zero_position.read()) * self.native_per_mm * self.factor.read()
        self.limits.write(min_value, max_value, self.native_units)


# --- gui -----------------------------------------------------------------------------------------


class GUI(BaseGUI):
    pass

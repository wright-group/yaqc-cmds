# TODO: record degree of microstepping in data file


### import ####################################################################

import time

import numpy as np

import pycmds.project.project_globals as g
from hardware.filters.filters import Driver as BaseDriver
from hardware.filters.filters import GUI as BaseGUI
import pycmds.project.com_handler as com_handler



### driver ####################################################################


class Driver(BaseDriver):
    def __init__(self, *args, **kwargs):
        BaseDriver.__init__(self, *args, **kwargs)
        self.index = kwargs["index"]

    def close(self):
        self.port.close()

    def home(self, inputs=[]):
        position = self.get_position()
        self.port.write(" ".join(["H", str(self.index)]))
        self.wait_until_ready()
        self.motor_position.write(0)
        self.get_position()
        self.set_position(position)

    def get_position(self):
        position = (
            (self.motor_position.read() - self.zero_position.read())
            * self.native_per_deg
            * self.factor.read()
        )
        self.position.write(position, "deg")
        return position

    def initialize(self):
        # open com port
        port_index = self.hardware_ini.read(self.name, "serial_port")
        self.port = com_handler.get_com(port_index, timeout=100000)  # timeout in 100 seconds
        # stepping
        self.microsteps = self.hardware_ini.read(self.name, "degree_of_microstepping")
        steps_per_rotation = (
            self.hardware_ini.read(self.name, "full_steps_per_rotation") * self.microsteps
        )
        self.degrees_per_step = 360.0 / steps_per_rotation
        self.port.write("U %i" % self.microsteps)
        # finish
        self.initialized.write(True)
        self.initialized_signal.emit()
        self.wait_until_ready()

    def is_busy(self):
        # KFS 2018-05-22: Attempted to write an actual is_busy
        # Resulted in timeout at shutdown time for some reason
        return False

    def set_degrees(self, degrees):
        change = degrees - self.motor_position.read()
        steps = np.floor(change / self.degrees_per_step)
        signed_steps = steps
        command = " ".join(["M", str(self.index), str(signed_steps)])
        self.port.write(command)
        self.wait_until_ready()
        # update own position
        motor_position = self.motor_position.read()
        motor_position += steps * self.degrees_per_step
        self.motor_position.write(motor_position)
        self.get_position()

    def set_position(self, destination):
        self.set_degrees(
            self.zero_position.read("deg")
            + destination / (self.native_per_deg * self.factor.read())
        )
        self.save_status()

    def wait_until_ready(self):
        while True:
            command = " ".join(["Q", str(self.index)])
            if not self.port.is_open():
                return
            status = self.port.write(command, then_read=True).rstrip()
            if status == "R":
                break
            time.sleep(0.1)
        self.port.flush()


### gui #######################################################################


class GUI(BaseGUI):
    pass

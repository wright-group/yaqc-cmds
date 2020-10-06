# --- import --------------------------------------------------------------------------------------


import pathlib
import time

import toml
import appdirs

import WrightTools as wt
import yaqc

import pycmds.project.project_globals as g
import pycmds.project.widgets as pw
import pycmds.project.classes as pc
import pycmds.hardware.hardware as hw

# --- driver --------------------------------------------------------------------------------------


class Driver(hw.Driver):
    def __init__(self, *args, **kwargs):
        self.yaqd_port = kwargs["yaqd_port"]
        self.yaqd_host = kwargs.get("yaqd_host", "127.0.0.1")
        self.motor = yaqc.Client(self.yaqd_port, host=self.yaqd_host)
        self.motor_units = self.motor.get_units()
        if self.motor_units == "deg":
            self.motor_units = "deg_filter_wheel"
        self.native_units = kwargs.get("native_units", "deg")
        self.native_per_motor = float(wt.units.convert(1, self.motor_units, self.native_units))
        hw.Driver.__init__(self, *args, **kwargs)
        id_ = self.motor.id()
        if id_["model"] is not None:
            self.hardware.model = id_["model"]
        elif id_["kind"].startswith("fake"):
            self.hardware.model = "fake"
        else:
            self.hardware.model = id_["kind"]

        self.factor = self.hardware.factor
        self.factor.write(kwargs["factor"])
        self.motor_limits = self.hardware.motor_limits
        self.motor_limits.write(*self.motor.get_limits())
        self.motor_position = self.hardware.motor_position
        self.zero_position = self.hardware.zero_position
        self.set_zero(self.zero_position.read(self.motor_units))
        self.recorded["_".join([self.name, "zero"])] = [
            self.zero_position,
            "deg",
            0,
            self.label.read(),
            True,
        ]
        
    def initialize(self):
        # This should be unnecessary at some point, once everything is yaq
        self.get_position()
        self.initialized.write(True)
        self.initialized_signal.emit()
        
    def is_busy(self):
        return self.motor.busy()
        
    def get_position(self):
        position = self.motor.get_position()
        self.motor_position.write(position)
        delay = (
            (position - self.zero_position.read(self.motor_units))
            * self.native_per_motor
            * self.factor.read()
        )
        self.position.write(delay, self.native_units)
        return delay
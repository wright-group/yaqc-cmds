### import ####################################################################


import time
import collections

import project.classes as pc
import project.project_globals as g


### define ####################################################################


main_dir = g.main_dir.read()


### driver ####################################################################


class PoyntingCorrectionDevice(object):
    def __init__(self, native_units="wn"):
        self.native_units = native_units
        self.limits = pc.NumberLimits(units=self.native_units)
        self.offset = pc.Number(initial_value=0, units=self.native_units, display=True)
        # TODO: not use hardcoded Phi and Theta as motor names, read from curve
        self.recorded = collections.OrderedDict()
        self.motor_names = ["Phi", "Theta"]
        self.motor_positions = collections.OrderedDict()
        self.motor_positions["Phi"] = pc.Number()
        self.motor_positions["Theta"] = pc.Number()
        self.motors = []
        self.initialized = pc.Bool()

    def _get_motor_position(self, index):
        raise NotImplementedError

    def _home(self, index):
        raise NotImplementedError

    def _initialize(self, inputs):
        raise NotImplementedError

    def _set_motor(self, index, position):
        raise NotImplementedError

    def _zero(self, index):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def get_motor_position(self, motor):
        # get motor index
        if isinstance(motor, str):
            motor_index = self.motor_names.index(motor)
        elif isinstance(motor, int):
            motor_index = motor
            motor = self.motor_name.index(motor)
        else:
            print(
                "motor_index not recognized in PoyntingCorrectionDevice get_motor_position"
            )
            return
        # read position
        position = self._get_motor_position(motor_index)
        self.motor_positions[motor].write(position)
        return position

    def get_motor_positions(self):
        return [self.get_motor_position(s) for s in self.motor_names]

    def home(self, motor=None):
        if motor == None:
            for m in range(len(self.motor_names)):
                self._home(m)
        elif isinstance(motor, str):
            self._home(self.motor_names.index(motor))
        elif isinstance(motor, int):
            self._home(motor)
        else:
            self._home(self.motors.index(motor))

    def initialize(self, OPA):
        self.OPA = OPA
        self.motor_positions = collections.OrderedDict()
        motor_limits = self.motor_limits()
        for motor_index, motor_name in enumerate(self.motor_names):
            number = pc.Number(
                name=motor_name,
                initial_value=0,
                decimals=0,
                limits=motor_limits,
                display=True,
            )
            self.motor_positions[motor_name] = number
            self.recorded["%s_%s" % (self.OPA.name, motor_name)] = [
                number,
                None,
                1,
                motor_name.lower(),
            ]
        self._initialize()
        self.initialized.write(True)

    def is_busy(self):
        raise NotImplementedError

    def motor_limits(self):
        raise NotImplementedError

    def move_rel(self, motor, position):
        if str(motor) in self.motor_names:
            self._move_rel(self.motor_names.index(motor), int(position))
        elif isinstance(motor, int):
            self._move_rel(motor, int(position))
        else:
            self._move_rel(self.motors.index(motor), int(position))

    def set_motor(self, motor, position):
        if str(motor) in self.motor_names:
            self._set_motor(self.motor_names.index(motor), int(position))
        elif isinstance(motor, int):
            self._set_motor(motor, int(position))
        else:
            self._set_motor(self.motors.index(motor), int(position))
        self.get_motor_positions()

    def wait_until_still(self):
        while self.is_busy():
            time.sleep(0.1)
            self.get_motor_positions()
        self.get_motor_positions()

    def zero(self, motor=None):
        if motor == None:
            for m in range(len(self.motor_names)):
                self._zero(m)
        elif isinstance(motor, str):
            self._zero(self.motor_names.index(motor))
        elif isinstance(motor, int):
            self._zero(motor)
        else:
            self._zero(self.motors.index(motor))

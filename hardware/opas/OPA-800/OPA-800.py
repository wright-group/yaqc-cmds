### import ####################################################################

import collections

import numpy as np

import attune
import yaqd_core

import project.classes as pc
import project.project_globals as g
from hardware.opas.opas import Driver as BaseDriver
from hardware.opas.opas import GUI as BaseGUI


### define ####################################################################


main_dir = g.main_dir.read()


### driver ####################################################################


class Driver(BaseDriver):

    def __init__(self, *args, **kwargs):
        self.motor_names = kwargs.pop("motor_names", ['Grating', 'BBO', 'Mixer'])
        self.motor_ports = kwargs.pop("motor_ports")
        self.motors = {}
        self.curve_paths = collections.OrderedDict()
        # TODO: Determine if pico_opa needs to have interaction string combo
        allowed_values = ['SHS']
        self.interaction_string_combo = pc.Combo(allowed_values=allowed_values)
        BaseDriver.__init__(self, *args, **kwargs)
        # load curve
        self.curve_path = pc.Filepath(ini=self.hardware_ini, section=self.name, option='curve_path',
                                      import_from_ini=True, save_to_ini_at_shutdown=True, options=['Curve File (*.curve)'])
        self.curve_path.updated.connect(self.curve_path.save)
        self.curve_path.updated.connect(lambda: self.load_curve())

        self.curve_paths['Curve'] = self.curve_path
        self.load_curve()

    def _load_curve(self, interaction):
        '''
        when loading externally, write to curve_path object directly
        '''
        self.curve = attune.Curve.read(self.curve_paths['Curve'].read())
        self.curve.kind = "opa800"
        return self.curve

    def _set_motors(self, motor_destinations):
        for axis, dest in motor_destinations.items():
            if dest >= 0 and dest <= 50:
                self.motors[axis].set_position(float(dest))

    def get_motor_positions(self):
        for i in self.motors:
            val = self.motors[i].get_position()
            self.motor_positions[i].write(val)
        if self.poynting_correction:
            self.poynting_correction.get_motor_positions()

    def initialize(self):
        self.serial_number = -1
        self.recorded['w%d' % self.index] = [self.position, self.native_units, 1., str(self.index)]
        # motor positions
        motor_limits = pc.NumberLimits(min_value=0, max_value=50)
        for motor_index, motor_name in enumerate(self.motor_names):
            if motor_name in ['Phi', 'Theta']:
                continue
            number = pc.Number(name=motor_name, initial_value=25.,
                               decimals=6, limits=motor_limits, display=True)
            self.motor_positions[motor_name] = number
            self.motors.update({ motor_name: yaqd_core.Client(self.motor_ports[motor_index])})
            self.recorded['w%d_%s' % (self.index, motor_name)] = [
                number, None, 0.001, motor_name.lower()]
        # self.get_motor_positions()
        # tuning
        self.best_points = {}
        self.best_points['SHS'] = np.linspace(13500, 18200, 21)
        self.best_points['DFG'] = np.linspace(1250, 2500, 11)
        # finish
        BaseDriver.initialize(self)

    def is_busy(self):
        for motor in self.motors.values():
            if motor.busy():
                self.get_position()
                return True
        self.get_position()
        return False


### gui #######################################################################


class GUI(BaseGUI):
    pass

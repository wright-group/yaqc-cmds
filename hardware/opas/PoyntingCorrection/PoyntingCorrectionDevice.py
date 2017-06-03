### import ####################################################################


import os
import time
import collections

import numpy as np
import WrightTools as wt

import project.classes as pc
import project.project_globals as g
from project.ini_handler import Ini


### define ####################################################################


main_dir = g.main_dir.read()


### driver ####################################################################


class PoyntingCorrectionDevice(object):

    def __init__(self, native_units='wn'):
        self.native_units=native_units
        self.limits=pc.NumberLimits(units=self.native_units)
        self.offset = pc.Number(initial_value=0,units=self.native_units, display=True)
        self.recorded = collections.OrderedDict()
        self.motor_names = ['phi', 'theta']
        self.motors = []
        self.ini = Ini(os.path.join(main_dir, 'hardware', 'opas', 'PoyntingCorrection', 'PoyntingCorrection.ini'))
        self.initialized = pc.Bool()

    def _get_motor_position(self, index):
        raise NotImplementedError

    def _home(self, index):
        raise NotImplementedError

    def _initialize(self,inputs):
        raise NotImplementedError

    def _set_motor(self, index, position):
        raise NotImplementedError

    def _zero(self, index):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def get_crv_paths(self):
        return [self.curve_path.read()]

    def get_points(self):
        return self.curve.colors

    def get_motor_position(self, motor):
        if isinstance(motor, str):
            return self._get_motor_position(self.motor_names.index(motor))
        elif isinstance(motor,int):
            return self._get_motor_position(motor)
        else:
            return self._get_motor_position(self.motors.index(motor))

    def get_motor_positions(self, inputs=[]):
        return [self.get_motor_position(s) for s in self.motor_names]

    def home(self, motor=None):
        if motor==None:
            for m in range(len(self.motor_names)):
                self._home(m)
        elif isinstance(motor, str):
            self._home(self.motor_names.index(motor))
        elif isinstance(motor,int):
            self._home(motor)
        else:
            self._home(self.motors.index(motor))

    def initialize(self, OPA):
        self.address = OPA
        self.index = OPA.index
        self.motor_positions = collections.OrderedDict()
        motor_limits = self.motor_limits()
        for motor_index, motor_name in enumerate(self.motor_names):
            number = pc.Number(name=motor_name,initial_value = 0, decimals=0,limits=motor_limits,display=True)
            self.motor_positions[motor_name] = number
            self.recorded['w%d_%s'%(self.index,motor_name)] = [number,None,1,motor_name.lower()]    
        self._initialize()
        self.curve_path = pc.Filepath(ini=self.ini, section='OPA%d'%self.index, option='curve path', import_from_ini=True, save_to_ini_at_shutdown=True, options=['Curve File(*.curve)'])
        self.curve_path.updated.connect(self.curve_path.save)
        self.curve_path.updated.connect(lambda: self.load_curve(self.curve_path.read()))
        self.load_curve(self.curve_path.read())
        self.initialized.write(True)

    def is_busy(self):
        raise NotImplementedError

    def load_curve(self, path):
        self.curve = wt.tuning.curve.from_poynting_curve(path)
        min_color = self.curve.colors.min()
        max_color = self.curve.colors.max()
        self.limits.write(min_color, max_color, self.native_units)

    def motor_limits(self):
        raise NotImplementedError

    def move_rel(self, motor, position):
        if isinstance(motor, str):
            self._move_rel(self.motor_names.index(motor), position)
        elif isinstance(motor,int):
            self._move_rel(motor, position)
        else:
            self._move_rel(self.motors.index(motor),position)

    def set_motor(self, motor, position):
        if isinstance(motor, str):
            self._set_motor(self.motor_names.index(motor), position)
        elif isinstance(motor,int):
            self._set_motor(motor, position)
        else:
            self._set_motor(self.motors.index(motor), position)

    def set_position(self, color):
        color = np.clip(color, self.curve.colors.min(), self.curve.colors.max())
        motor_destinations = self.curve.get_motor_positions(color, self.native_units)
        motor_names = self.curve.get_motor_names()
        motor_destinations = self.curve.get_motor_positions(color, self.native_units)
        for n in self.motor_names:
            index = motor_names.index(n)
            self.set_motor(n,motor_destinations[index])

    def wait_until_still(self):
        while self.is_busy():
            time.sleep(0.1)
            self.get_motor_positions()
        self.get_motor_positions()

    def zero(self, motor=None):
        if motor==None:
            for m in range(len(self.motor_names)):
                self._zero(m)
        elif isinstance(motor, str):
            self._zero(self.motor_names.index(motor))
        elif isinstance(motor,int):
            self._zero(motor)
        else:
            self._zero(self.motors.index(motor))

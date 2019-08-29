# --- import --------------------------------------------------------------------------------------


import os
import time
import copy
import collections

import numpy as np

import ctypes
from ctypes import *

import attune

import project
import project.classes as pc
import project.project_globals as g
from project.ini_handler import Ini
from hardware.opas.opas import Driver as BaseDriver
from hardware.opas.opas import GUI as BaseGUI
from hardware.opas.TOPAS.TOPAS_API import TOPAS_API
from attune.curve._topas import TOPAS_interaction_by_kind
                                 
# --- define --------------------------------------------------------------------------------------


main_dir = g.main_dir.read()


# --- driver --------------------------------------------------------------------------------------


class Driver(BaseDriver):

    def __init__(self, *args, **kwargs):
        self.motors={}
        self.curve_paths = collections.OrderedDict()
        self.ini = project.ini_handler.Ini(os.path.join(main_dir, 'hardware', 'opas', 'TOPAS', 'TOPAS.ini'))
        self.has_shutter = kwargs['has_shutter']
        if self.has_shutter:
            self.shutter_position = pc.Bool(name='Shutter', display=True, set_method='set_shutter')
        BaseDriver.__init__(self, *args, **kwargs)  
        if self.has_shutter:
            self.exposed += [self.shutter_position]
        # tuning curves
        self.serial_number = self.ini.read('OPA' + str(self.index), 'serial number')
        self.TOPAS_ini_filepath = os.path.join(g.main_dir.read(), 'hardware', 'opas', 'TOPAS', 'configuration', str(self.serial_number) + '.ini')
        self.TOPAS_ini = Ini(self.TOPAS_ini_filepath)
        self.TOPAS_ini.return_raw = True
        for curve_type in self.curve_indices.keys():
            section = 'Optical Device'
            option = 'Curve ' + str(self.curve_indices[curve_type])
            initial_value = self.TOPAS_ini.read(section, option)
            options = ['CRV (*.crv)']
            curve_filepath = pc.Filepath(initial_value=initial_value, options=options)
            curve_filepath.updated.connect(self.load_curve)
            self.curve_paths[curve_type] = curve_filepath
        # interaction string
        paths = self.curve_paths.copy()
        paths.pop("Poynting", None)
        paths = [v.read() for v in paths.values()]
        all_crvs = attune.TopasCurve.read_all(paths)
        allowed_values = list(all_crvs.keys())
        self.interaction_string_combo = pc.Combo(allowed_values=allowed_values)
        current_value = self.ini.read('OPA%i'%self.index, 'current interaction string')
        self.interaction_string_combo.write(current_value)
        self.interaction_string_combo.updated.connect(self.load_curve)
        g.queue_control.disable_when_true(self.interaction_string_combo)
        self.load_curve(update = False)

    def _get_motor_index(self, name):
        c = self.curve
        while c is not None:
            if name in c.dependents:
                return c[name].index
            c = c.subcurve
        raise KeyError(name)

    def _home_motors(self, motor_names):
        motor_indexes = []
        c = self.curve
        while len(motor_names):
            for m in motor_names:
                if m in c.dependents:
                    motor_indexes.append(c[m].index)
                    motor_names.pop(name)
            c = c.subcurve

        section = 'OPA' + str(self.index)
        # close shutter
        if self.has_shutter:
            original_shutter = self.shutter_position.read()
            self.set_shutter([False])
        # record current positions
        original_positions = []
        for motor_index in motor_indexes:
            error, position = self.api.get_motor_position(motor_index)
            original_positions.append(position)
        # send motors to left reference switch ----------------------------------------------------
        # set all max, current positions to spoof values
        overflow = 8388607
        for motor_index in motor_indexes:
            self.api.set_motor_positions_range(motor_index, 0, overflow)
            self.api.set_motor_position(motor_index, overflow)
        # send motors towards zero
        for motor_index in motor_indexes:
            self.api.start_motor_motion(motor_index, 0)
        # wait for motors to hit left reference switch
        motor_indexes_not_homed = copy.copy(motor_indexes)
        while len(motor_indexes_not_homed) > 0:
            for motor_index in motor_indexes_not_homed:
                time.sleep(0.1)
                error, left, right = self.api.get_reference_switch_status(motor_index)
                if left:
                    motor_indexes_not_homed.remove(motor_index)
                    # set counter to zero
                    self.api.set_motor_position(motor_index, 0)
        # send motors to 400 steps ----------------------------------------------------------------
        for motor_index in motor_indexes:
            self.api.start_motor_motion(motor_index, 400)
        self.wait_until_still()
        # send motors left reference switch slowly ------------------------------------------------
        # set motor speed
        for motor_index in motor_indexes:
            min_velocity = self.ini.read(section, 'motor {} min velocity (us/s)'.format(motor_index))
            max_velocity = self.ini.read(section, 'motor {} max velocity (us/s)'.format(motor_index))
            acceleration = self.ini.read(section, 'motor {} acceleration (us/s^2)'.format(motor_index))
            error = self.api.set_speed_parameters(motor_index, min_velocity, int(max_velocity/2), acceleration)
        # set all max, current positions to spoof values
        for motor_index in motor_indexes:
            self.api.set_motor_positions_range(motor_index, 0, overflow)
            self.api.set_motor_position(motor_index, overflow)
        # send motors towards zero
        for motor_index in motor_indexes:
            self.api.start_motor_motion(motor_index, 0)
        # wait for motors to hit left reference switch
        motor_indexes_not_homed = copy.copy(motor_indexes)
        while len(motor_indexes_not_homed) > 0:
            for motor_index in motor_indexes_not_homed:
                time.sleep(0.1)
                error, left, right = self.api.get_reference_switch_status(motor_index)
                if left:
                    motor_indexes_not_homed.remove(motor_index)
                    # set counter to zero
                    self.api.set_motor_position(motor_index, 0)
        # send motors to 400 steps (which is now true zero) ---------------------------------------
        for motor_index in motor_indexes:
            self.api.start_motor_motion(motor_index, 400)
        self.wait_until_still()
        for motor_index in motor_indexes:
            self.api.set_motor_position(motor_index, 0)
        # finish ----------------------------------------------------------------------------------
        # set speed back to real values
        for motor_index in motor_indexes:
            min_velocity = self.ini.read(section, 'motor {} min velocity (us/s)'.format(motor_index))
            max_velocity = self.ini.read(section, 'motor {} max velocity (us/s)'.format(motor_index))
            acceleration = self.ini.read(section, 'motor {} acceleration (us/s^2)'.format(motor_index))
            error = self.api.set_speed_parameters(motor_index, min_velocity, max_velocity, acceleration)
        # set range back to real values
        for motor_index in motor_indexes:
            min_position = self.ini.read(section, 'motor {} min position (us)'.format(motor_index))
            max_position = self.ini.read(section, 'motor {} max position (us)'.format(motor_index))
            error = self.api.set_motor_positions_range(motor_index, min_position, max_position)
        # launch return motion
        for motor_index, position in zip(motor_indexes, original_positions):
            self.api.start_motor_motion(motor_index, position)
        # wait for motors to finish moving
        self.wait_until_still()
        # return shutter
        if self.has_shutter:
            self.set_shutter([original_shutter])

    def _load_curve(self, interaction):
        interaction = self.interaction_string_combo.read()
        curve_paths_copy = self.curve_paths.copy()
        if 'Poynting' in curve_paths_copy.keys():
            del curve_paths_copy['Poynting']
        crv_paths = [m.read() for m in curve_paths_copy.values()]
        all_curves = attune.TopasCurve.read_all(crv_paths)
        self.interaction_string_combo.set_allowed_values(list(all_curves.keys()))
        self.curve = all_curves[interaction]
        return self.curve
       
    def _set_motors(self, motor_destinations):
        for motor_name, destination in motor_destinations.items():
            motor_index = self._get_motor_index(motor_name)
            error, destination_steps = self.api.convert_position_to_steps(motor_index, destination)
            self.api.start_motor_motion(motor_index, destination_steps)

    def _update_api(self, interaction):
        # write to TOPAS ini
        self.api.close()
        for curve_type, curve_path_mutex in self.curve_paths.items():
            if curve_type == 'Poynting':
                continue
            curve_path = curve_path_mutex.read()            
            section = 'Optical Device'
            option = 'Curve ' + str(self.curve_indices[curve_type])
            self.TOPAS_ini.write(section, option, curve_path)
        self.api = TOPAS_API(self.TOPAS_ini_filepath)
        # save current interaction string
        self.ini.write('OPA%i'%self.index, 'current interaction string', interaction)

    def _wait_until_still(self):
        while self.is_busy():
            time.sleep(0.1)

    def close(self):
        if self.has_shutter:
            self.api.set_shutter(False)
        self.api.close()

    def get_motor_positions(self):
        for i in range(6):
            motor_mutex = list(self.motor_positions.values())[i]
            error, position_steps = self.api.get_motor_position(i)
            error, position = self.api.convert_position_to_units(i, position_steps)
            motor_mutex.write(position)
        if self.poynting_correction:
            self.poynting_correction.get_motor_positions()
    
    def get_speed_parameters(self, inputs):
        motor_index = inputs[0]
        error, min_speed, max_speed, acceleration = self.api._get_speed_parameters(motor_index)
        return [error, min_speed, max_speed, acceleration]

    def initialize(self):
        self.serial_number = self.ini.read('OPA' + str(self.index), 'serial number')
        # load api
        self.api = TOPAS_API(self.TOPAS_ini_filepath)
        if self.has_shutter:
            self.api.set_shutter(False)
        
        # motor positions
        for motor_index, motor_name in enumerate(self.motor_names):
            error, min_position_steps, max_position_steps = self.api.get_motor_positions_range(motor_index)
            valid_position_steps = np.arange(min_position_steps, max_position_steps+1)
            valid_positions_units = [self.api.convert_position_to_units(motor_index, s)[1] for s in valid_position_steps]
            min_position = min(valid_positions_units)
            max_position = max(valid_positions_units)
            limits = pc.NumberLimits(min_position, max_position)
            number = pc.Number(initial_value=0, limits=limits, display=True, decimals=6)
            self.motor_positions[motor_name] = number
            self.recorded['w%d_'%self.index + motor_name] = [number, None, 1., motor_name]
        # finish
        BaseDriver.initialize(self)

    def is_busy(self):
        if self.api.open:
            error, still = self.api.are_all_motors_still()
            print('TOPAS is busy', error, still)
            return not still
        else:
            return False  # for shutdown
    
    def set_shutter(self, inputs):
        shutter_state = inputs[0]
        error = self.api.set_shutter(shutter_state)
        self.shutter_position.write(shutter_state)
        return error
         
    def set_speed_parameters(self, inputs):
        motor_index, min_speed, max_speed, accelleration = inputs
        error = self.api._set_speed_parameters(motor_index, min_speed, max_speed, acceleration)
        return error


# --- gui -----------------------------------------------------------------------------------------


class GUI(BaseGUI):
    pass

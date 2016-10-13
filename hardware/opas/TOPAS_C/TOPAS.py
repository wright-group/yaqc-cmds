### import ####################################################################


import os
import time
import copy
import collections

import numpy as np

from types import FunctionType
from functools import wraps

from PyQt4 import QtGui, QtCore

import ctypes
from ctypes import *

import WrightTools as wt
import WrightTools.units as wt_units

import project.classes as pc
import project.widgets as pw
import project.project_globals as g
from project.ini_handler import Ini
main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'hardware', 'opas',
                                 'TOPAS_C',
                                 'TOPAS.ini'))
                                 
                                 
### define ####################################################################
                                 
 
error_dict = {0 : None,
              1 : 'Unknown error',
              2 : 'No TOPAS USB devices found',
              3 : 'Invalid device instance',
              4 : 'Invalid device index',
              5 : 'Buffer too small',
              6 : 'Failed to get TOPAS USB serial number',
              7 : 'Device already opened',
              8 : 'Device failed to open',
              9 : 'USB communication channel failed to open',
              10: 'USB read error',
              11: 'Motor configuration failed to load',
              12: 'Configuration file doesn\'t match board configuration',
              13: 'Transmission of parameters failed',
              14: 'Device with this serial number not found',
              15: 'Invalid interface card type',
              16: 'Device has not been opened',
              17: 'USB command failed to receive response',
              18: 'Wavelength cannot be set',
              19: 'Invalid motor index',
              20: 'Function is not supported by LPT card',
              21: 'Invalid stage code',
              22: 'Invalid stage code',
              23: 'Tuning curve file failed to load',
              24: 'Tuning curve file read error',
              25: 'Wrong tuning curve file version',
              26: 'Wrong tuning curve type',
              27: 'Invalid number of motors',
              28: 'Invalid number of interactions',
              29: 'OPA type mismatch',
              30: 'Invalid wavelength',
              31: 'Invalid grating motor index in OPA tuning file',
              32: 'Tuning curve type mismatch',
              33: 'Configuration file not found',
              34: 'Invalid wavelength for this combination'}
              
              
curve_indicies = {'Base': 1,
                  'Mixer 1': 2,
                  'Mixer 2': 3,
                  'Mixer 3': 4}


### api object ################################################################


#IMPORTANT: THE WINDLL CALL MUST HAPPEN WITHIN THE TOPAS DRIVER FOLDER (os.chdir())

driver_folder = os.path.join(main_dir, 'hardware', 'opas', 'TOPAS_C', 'configuration', 'drivers')
os.chdir(driver_folder)
dll_path = os.path.join(driver_folder, 'TopasAPI.dll')
dll = ctypes.WinDLL(dll_path)
os.chdir(main_dir)

dll_busy = pc.Busy()

# NOTE: Cannot load more than 3 TOPAS OPAs (DLL restriction)
indicies = {}

class TOPAS():
    
    def __init__(self, ini_filepath):
        self.open = False
        self.ini_filepath = ini_filepath
        # get index
        serial = int(os.path.basename(self.ini_filepath).split('.')[0])
        if serial not in indicies.keys():
            indicies[serial] = len(indicies.keys())
        self.index = indicies[serial]
        # open
        self._open_device(self.ini_filepath)
        
    def _open_device(self, ini_filepath):
        '''
        int index, str ini_filepath \n
        index between 0 and 3 \n
        returns [assigned index]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_OpenDevice(c_ushort(self.index), ini_filepath)
        dll_busy.write(False)
        # finish
        self.open = True
        return [error]
        
    def are_all_motors_still(self):
        '''
        returns [error, bool result]
        '''
        # prepare
        result = c_void_p()
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_AreAllMotorsStill(c_ushort(self.index), pointer(result))
        dll_busy.write(False)
        # finish
        return [error, bool(result)]
        
    def close(self):
        '''
        int index \n
        returns [error code]
        '''
        # prepare
        index = c_ushort(self.index)
        serial_number = self._get_device_serial_number()[1]
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_CloseDevice(index)
        dll_busy.write(False)
        # finish
        self.open = False
        return [error]

    def convert_position_to_steps(self, motor_index, position):
        '''
        int motor_index, float position (absolute geometry) \n
        returns [error code, int position (microsteps)]
        '''
        # prepare
        steps = c_uint()
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_ConvertPositionToSteps(c_ushort(self.index), c_ushort(motor_index), c_double(position), pointer(steps))
        dll_busy.write(False)
        # finish
        return [error, int(steps.value)]
        
    def convert_position_to_units(self, motor_index, position):
        '''
        int motor index, int position (microsteps) \n
        returns [error code, float position (absolute geometery)] \n
        '''
        # prepare
        geometric_position = c_double()
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_ConvertPositionToUnits(c_ushort(self.index), c_ushort(motor_index), c_ushort(position), pointer(geometric_position))
        dll_busy.write(False)        
        # finish
        return [error, geometric_position.value]

    def _get_count_of_devices(self):
        '''
        returns [error code, int count_of_devices]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        count_of_devices = dll.Topas_GetCountOfDevices()
        dll_busy.write(False)  
        # finish
        # no error code is actually generated by dll, I fake it for the sake of consistency
        return [0, count_of_devices]
    
    def get_count_of_motors(self):
        '''
        returns [error code, int count_of_motors]
        '''
        # prepare
        number_of_device_motors =  c_ushort()
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_GetCountOfMotors(c_ushort(self.index), pointer(number_of_device_motors))
        dll_busy.write(False)
        # finish
        return [error, number_of_device_motors.value]

    def _get_device_serial_number(self):
        '''
        returns [error code, int device_serial_number]
        '''
        # prepare
        serial_number = c_ulong()
        size = 8
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_GetDeviceSerialNumber(c_ushort(self.index), pointer(serial_number), c_ushort(size))
        dll_busy.write(False)
        # finish
        return [error, int(serial_number.value)]
    
    def get_interaction(self, stage):
        '''
        int index, int stage \n
        returns [error code, int interaction]'
        '''
        # prepare
        interaction = c_ushort()
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_GetInteraction(c_ushort(self.index), c_ushort(stage), pointer(interaction))
        dll_busy.write(False)
        # finish
        return [error, interaction.value]

    def _get_motor_affix(self, motor_index):
        '''
        int index, int motor_index \n
        returns [error code, float motor_affix]
        '''
        # prepare
        motor_affix = c_double()
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_GetMotorAffix(c_ushort(self.index), c_ushort(motor_index), pointer(motor_affix))
        dll_busy.write(False)
        # finish
        return [error, motor_affix.value]

    def _get_motor_offset(self, stage, interaction_index, motor_index):
        '''
        int index, int stage, int interaction_index, int motor_index \n
        returns [error code, float offset]
        '''
        # prepare
        offset = c_double()
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_GetMotorOffset(c_ushort(self.index), c_ushort(stage), c_ushort(interaction_index), c_ushort(motor_index), pointer(offset))
        dll_busy.write(False)        
        # finish        
        return [error, offset.value]

    def get_motor_position(self, motor_index):
        '''
        int index, int motor_index \n
        returns [error code, position]
        '''
        # prepare
        position = c_uint()
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_GetMotorPosition(c_ushort(self.index), c_ushort(motor_index), pointer(position))
        dll_busy.write(False) 
        # finish
        return [error, int(position.value)]

    def get_motor_positions_range(self, motor_index):
        '''
        int index, int motor_index \n
        returns [error code, min_position, max_position]
        '''
        # prepare
        min_position = c_uint()
        max_position = c_uint()
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_GetMotorPositionsRange(c_ushort(self.index), c_ushort(motor_index), pointer(min_position), pointer(max_position))
        dll_busy.write(False)        
        # finish        
        return [error, int(min_position.value), int(max_position.value)]
        
    def get_reference_switch_status(self, motor_index):
        '''
        int index, int motor_index \n
        reference switches will return as true when limit switch is depressed \n
        returns [error code, bool left_reference_switch, bool right_reference_switch]
        '''
        # prepare
        left_reference_switch = c_ushort()
        right_reference_switch = c_ushort()
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_GetReferenceSwitchStatus(c_ushort(self.index), c_ushort(motor_index), pointer(left_reference_switch), pointer(right_reference_switch))
        dll_busy.write(False) 
        # finish        
        return [error, bool(left_reference_switch), bool(right_reference_switch)]

    def _get_speed_parameters(self, motor_index):
        '''
        int motor_index \n
        returns [error code, int min_speed, int max_speed, int acceleration]
        '''
        # prepare
        min_speed = c_uint()
        max_speed = c_uint()
        acceleration = c_uint()
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.TopasUSB_GetSpeedParams(c_ushort(self.index), c_ushort(motor_index), pointer(min_speed), pointer(max_speed), pointer(acceleration))
        dll_busy.write(False)         
        # finish        
        return [error, int(min_speed.value), int(max_speed.value), int(acceleration.value)]

    def get_wavelength(self, stage):
        '''
        int index, int stage \n
        returns [error code, float wavelength (nm)]
        '''
        # prepare
        wavelength = c_float()
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_GetWl(c_ushort(self.index), c_ushort(stage), pointer(wavelength))
        dll_busy.write(False)
        # finish
        return [error, float(wavelength.value)]

    def is_motor_still(self, motor_index):
        '''
        int index, int motor_index \n
        returns [error code, bool result]
        '''
        # prepare
        result = c_void_p()
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_IsMotorStill(c_ushort(self.index), c_ushort(motor_index), pointer(result))
        dll_busy.write(False)
        # finish
        return [error, bool(result)]

    def _is_wavelength_setting_finished(self):
        '''
        int index \n
        returns [error code, bool result]
        '''
        # prepare
        result = c_void_p()
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_IsWavelengthSettingFinished(c_ushort(self.index), pointer(result))
        dll_busy.write(False)
        # finish
        return [error, bool(result)]

    def move_motor(self, motor_index, new_position):
        '''
        get_interaction
        int index, int motor_index, int_new_position \n
        new_position in microsteps \n
        returns [error code]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_MoveMotor(c_ushort(self.index), c_ushort(motor_index), c_uint(new_position))
        dll_busy.write(False)
        # finish
        return [error]
        
    def move_motor_to_position_units(self, motor_index, position):
        '''
        int motor_index, float position (absolute geometry) \n
        returns [error code]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_MoveMotorToPositionInUnits(c_ushort(self.index), c_ushort(motor_index), c_double(position))
        dll_busy.write(False)
        # finish
        return [error]
        
    def set_shutter(self, shutter_state):
        '''
        int index, bool shutter_state \n
        shutter open when shutter_state = True \n
        returns [error code]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_OpenShutter(c_ushort(self.index), c_ushort(not shutter_state))
        dll_busy.write(False)
        # finish
        return [error]
        
    def _set_motor_affix(self, motor_index, affix):
        '''
        int motor index, float affix (absolute geometry) \n
        returns [error code]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_SetMotorAffix(c_ushort(self.index), c_ushort(motor_index), c_double(affix))
        dll_busy.write(False)
        # finish
        return [error]
        
    def _set_motor_offset(self, stage, interaction, motor_index):
        '''
        int stage, int interaction, int motor_index, float offset (relative geometry) \n
        returns [error code]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_SetMotorOffset(c_ushort(self.index), c_ushort(stage), c_ushort(interaction), c_ushort(motor), c_double(offset))
        dll_busy.write(False)
        # finish
        return [error]
    
    def set_motor_position(self, motor_index, counter_position):
        '''
        int motor_index, int counter_position (microsteps) \n
        returns [error code]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_SetMotorPosition(c_ushort(self.index), c_ushort(motor_index), c_uint(counter_position))
        dll_busy.write(False)
        # finish
        return [error]

    def set_motor_positions_range(self, motor_index, min_position, max_position):
        '''
        int motor_index, int min_position (microsteps), int max_position (microsteps) \n
        returns [error code]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_SetMotorPositionsRange(c_ushort(self.index), c_ushort(motor_index), c_uint(min_position), c_uint(max_position))
        dll_busy.write(False)
        # finish
        return [error]
    
    def set_speed_parameters(self, motor_index, min_speed, max_speed, acceleration):
        '''
        int motor_index, int min_speed, int max_speed \n
        returns [error code]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.TopasUSB_SetSpeedParams(c_ushort(self.index), c_ushort(motor_index), c_uint(min_speed), c_uint(max_speed), c_uint(acceleration))
        dll_busy.write(False)
        # finish
        return [error]
    
    def _set_wavelength(self, wavelength):
        '''
        float wavelength \n
        returns [error code]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_SetWavelength(c_ushort(self.index), c_double(wavelength))
        dll_busy.write(False)
        # finish
        return [error]
        
    def _set_wavelength_ex(self, wavelength, base_interaction, mixer1_interaction, mixer2_interaction, mixer3_interaction):
        '''
        float wavelength, int base_interaction, int mixer1_interaction, int mixer2_interaction, int mixer3_interaction \n
        returns [error code]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_SetWavelengthEx(c_ushort(self.index), c_double(wavelength), c_ushort(base_interaction), c_ushort(mixer1_interaction), c_ushort(mixer2_interaction), c_ushort(mixer3_interaction))
        dll_busy.write(False)
        # finish
        return [error]
    
    def start_motor_motion(self, motor_index, towards):
        '''
        int motor_index, int towards (microsteps) \n
        returns [error code]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_StartMotorMotion(c_ushort(self.index), c_ushort(motor_index), c_uint(towards))
        dll_busy.write(False)
        # finish
        return [error]

    def _start_setting_wavelength(self, wavelength):
        '''
        float wavelength \n
        returns [error code]        
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_StartSettingWavelength(c_ushort(self.index), c_double(wavelength))
        dll_busy.write(False)
        # finish
        return [error]

    def _start_setting_wavelength_ex(self, wavelength, base_interaction, mixer1_interaction, mixer2_interaction, mixer3_interaction):
        '''
        float wavelength, int base_interaction, int mixer1_interaction, int mixer2_interaction, int mixer3_interaction \n
        returns [error code]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_StartSettingWavelengthEx(c_ushort(self.index), c_double(wavelength), c_ushort(base_interaction), c_ushort(mixer1_interaction), c_ushort(mixer2_interaction), c_ushort(mixer3_interaction))
        dll_busy.write(False)
        # finish
        return [error]
    
    def _stop_motor(self, motor_index):
        '''
        int motor_index \n
        returns [error code]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_StopMotor(c_ushort(self.index), c_ushort(motor_index))
        dll_busy.write(False)
        # finish
        return [error]
        
    def _update_motors_positions(self):
        '''
        returns [error code]
        '''
        # communicate
        while dll_busy.read():
            dll_busy.wait_for_update()
        dll_busy.write(True)
        error = dll.Topas_UpdateMotorsPositions(c_ushort(self.index))
        dll_busy.write(False)
        # finish
        return [error]


### OPA object ################################################################


class OPA:

    def __init__(self):
        self.native_units = 'nm'
        # mutex attributes
        self.limits = pc.NumberLimits(units=self.native_units)
        self.current_position = pc.Number(name='Color', initial_value=1300.,
                                          limits=self.limits,
                                          units=self.native_units, display=True,
                                          set_method='set_position')
        self.offset = pc.Number(initial_value=0, units=self.native_units, display=True)
        self.shutter_position = pc.Bool(name='Shutter',
                                        display=True, set_method='set_shutter')
        # objects to be sent to PyCMDS
        self.exposed = [self.current_position, self.shutter_position]
        self.recorded = collections.OrderedDict()
        self.motor_names = ['Crystal_1', 'Delay_1', 'Crystal_2', 'Delay_2', 'Mixer_1', 'Mixer_2', 'Mixer_3']
        # finish
        self.gui = GUI(self)
        self.initialized = pc.Bool()
        
    def _home_motors(self, motor_indexes):
        motor_indexes = list(motor_indexes)
        section = 'OPA' + str(self.index)
        # close shutter
        original_shutter = self.shutter_position.read()
        self.set_shutter([False])
        # record current positions
        original_positions = []
        for motor_index in motor_indexes:
            error, current_position = self.api.get_motor_position(motor_index)
            original_positions.append(current_position)
        # send motors to left reference switch --------------------------------
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
        # send motors to 400 steps --------------------------------------------
        for motor_index in motor_indexes:
            self.api.start_motor_motion(motor_index, 400)
        self.wait_until_still()
        # send motors left reference switch slowly ----------------------------
        # set motor speed
        for motor_index in motor_indexes:
            min_velocity = ini.read(section, 'motor {} min velocity (us/s)'.format(motor_index))
            max_velocity = ini.read(section, 'motor {} max velocity (us/s)'.format(motor_index))
            acceleration = ini.read(section, 'motor {} acceleration (us/s^2)'.format(motor_index))
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
        # send motors to 400 steps (which is now true zero) -------------------
        for motor_index in motor_indexes:
            self.api.start_motor_motion(motor_index, 400)
        self.wait_until_still()
        for motor_index in motor_indexes:
            self.api.set_motor_position(motor_index, 0)
        # finish --------------------------------------------------------------
        # set speed back to real values
        for motor_index in motor_indexes:
            min_velocity = ini.read(section, 'motor {} min velocity (us/s)'.format(motor_index))
            max_velocity = ini.read(section, 'motor {} max velocity (us/s)'.format(motor_index))
            acceleration = ini.read(section, 'motor {} acceleration (us/s^2)'.format(motor_index))
            error = self.api.set_speed_parameters(motor_index, min_velocity, max_velocity, acceleration)
        # set range back to real values
        for motor_index in motor_indexes:
            min_position = ini.read(section, 'motor {} min position (us)'.format(motor_index))
            max_position = ini.read(section, 'motor {} max position (us)'.format(motor_index))
            error = self.api.set_motor_positions_range(motor_index, min_position, max_position)
        # launch return motion
        for motor_index, position in zip(motor_indexes, original_positions):
            self.api.start_motor_motion(motor_index, position)
        # wait for motors to finish moving
        self.wait_until_still()
        # return shutter
        self.set_shutter([original_shutter])
        
    def _set_motors(self, motor_indexes, motor_destinations, wait=True):
        for motor_index, destination in zip(motor_indexes, motor_destinations):
            error, destination_steps = self.api.convert_position_to_steps(motor_index, destination)
            self.api.start_motor_motion(motor_index, destination_steps)
        if wait:
            self.wait_until_still()
        
    def close(self):
        self.api.set_shutter(False)
        self.api.close()
        
    def home_motor(self, inputs):
        motor_name = inputs[0]
        motor_index = self.motor_names.index(motor_name)
        self._home_motors([motor_index])
    
    def home_all(self, inputs=[]):
        self._home_motors(np.arange(len(self.motor_names)))

    def load_curve(self, inputs=[]):
        '''
        inputs can be none (so it loads current curves) 
        or ['curve type', filepath]
        '''
        # TODO: actually support external curve loading
        # write to TOPAS ini
        self.api.close()
        for curve_type, curve_path_mutex in self.curve_paths.items():
            curve_path = curve_path_mutex.read()            
            section = 'Optical Device'
            option = 'Curve ' + str(curve_indicies[curve_type])
            self.TOPAS_ini.write(section, option, curve_path)
            print section, option, curve_path
        self.api = TOPAS(self.TOPAS_ini_filepath)
        # update own curve object
        interaction = self.interaction_string_combo.read()
        crv_paths = [m.read() for m in self.curve_paths.values()]
        self.curve = wt.tuning.curve.from_TOPAS_crvs(crv_paths, 'TOPAS-C', interaction)
        # update limits
        min_nm = self.curve.colors.min()
        max_nm = self.curve.colors.max()
        self.limits.write(min_nm, max_nm, 'nm')
        # update position
        self.get_position()
        # save current interaction string
        ini.write('OPA%i'%self.index, 'current interaction string', interaction)
        
    def get_crv_paths(self):
        return [o.read() for o in self.curve_paths.values()]

    def get_points(self):
        return self.curve.colors

    def get_position(self):
        motor_indexes = [self.motor_names.index(n) for n in self.curve.get_motor_names(full=False)]
        motor_positions = [self.motor_positions.values()[i].read() for i in motor_indexes]
        position = self.curve.get_color(motor_positions, units='nm')        
        if not np.isnan(self.address.hardware.destination.read()):
            position = self.address.hardware.destination.read()
        self.current_position.write(position, 'nm')
        return position

    def get_motor_positions(self, inputs=[]):
        for motor_index, motor_mutex in enumerate(self.motor_positions.values()):
            error, position_steps = self.api.get_motor_position(motor_index)
            error, position = self.api.convert_position_to_units(motor_index, position_steps)
            motor_mutex.write(position)
    
    def get_speed_parameters(self, inputs):
        motor_index = inputs[0]
        error, min_speed, max_speed, acceleration = self.api._get_speed_parameters(motor_index)
        return [error, min_speed, max_speed, acceleration]

    def initialize(self, inputs, address):
        '''
        OPA initialization method. Inputs = [index]
        '''
        self.address = address
        self.index = inputs[0]
        self.serial_number = ini.read('OPA' + str(self.index), 'serial number')
        self.recorded['w%d'%self.index] = [self.current_position, 'nm', 1., str(self.index)]
        # load api 
        self.TOPAS_ini_filepath = os.path.join(g.main_dir.read(), 'hardware', 'opas', 'TOPAS_C', 'configuration', str(self.serial_number) + '.ini')
        self.api = TOPAS(self.TOPAS_ini_filepath)
        self.api.set_shutter(False)
        self.TOPAS_ini = Ini(self.TOPAS_ini_filepath)
        self.TOPAS_ini.return_raw = True
        # motor positions
        self.motor_positions = collections.OrderedDict()
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
        self.get_motor_positions()
        # tuning curves
        self.curve_paths = collections.OrderedDict()
        for curve_type in curve_indicies.keys():
            section = 'Optical Device'
            option = 'Curve ' + str(curve_indicies[curve_type])
            initial_value = self.TOPAS_ini.read(section, option)
            options = ['CRV (*.crv)']
            curve_filepath = pc.Filepath(initial_value=initial_value, options=options)
            curve_filepath.updated.connect(self.load_curve)
            self.curve_paths[curve_type] = curve_filepath
        # interaction string
        allowed_values = []
        for curve_path_mutex in self.curve_paths.values():
            with open(curve_path_mutex.read()) as crv:
                crv_lines = crv.readlines()
            for line in crv_lines:
                if 'NON' in line:
                    allowed_values.append(line.rstrip())
        self.interaction_string_combo = pc.Combo(allowed_values=allowed_values)
        current_value = ini.read('OPA%i'%self.index, 'current interaction string')
        self.interaction_string_combo.write(current_value)
        self.interaction_string_combo.updated.connect(self.load_curve)
        g.queue_control.disable_when_true(self.interaction_string_combo)
        self.load_curve()
        # finish
        self.get_position()
        self.initialized.write(True)
        self.address.initialized_signal.emit()       

    def is_busy(self):
        if self.api.open:
            error, still = self.api.are_all_motors_still()
            return not still
        else:
            return False

    def is_valid(self, destination):
        return True

    def set_offset(self, offset):
        pass

    def set_position(self, destination):
        # coerce destination to be within current tune range
        destination = np.clip(destination, self.curve.colors.min(), self.curve.colors.max())
        # get destinations from curve
        motor_names = self.curve.get_motor_names()
        motor_destinations = self.curve.get_motor_positions(destination, 'nm')
        # send command
        motor_indexes = [self.motor_names.index(n) for n in motor_names]
        self._set_motors(motor_indexes, motor_destinations)
        # finish
        self.get_position()
        
    def set_position_except(self, inputs):
        '''
        set position, except for motors that follow
        
        does not wait until still...
        '''
        destination = inputs[0]
        self.address.hardware.destination.write(destination)
        self.current_position.write(destination, 'nm')
        exceptions = inputs[1]  # list of integers
        motor_destinations = self.curve.get_motor_positions(destination, 'nm')
        motor_indexes = []
        motor_positions = []
        for i in [self.motor_names.index(n) for n in self.curve.get_motor_names()]:
            if i not in exceptions:
                motor_indexes.append(i)
                motor_positions.append(motor_destinations[i])
        self._set_motors(motor_indexes, motor_positions, wait=False)
        
    def set_motor(self, inputs):
        '''
        inputs [motor_name (str), destination (steps)]
        '''
        motor_name, destination = inputs
        motor_index = self.motor_names.index(motor_name)
        self._set_motors([motor_index], [destination])

    def set_motors(self, inputs):
        motor_indexes = range(len(inputs))
        motor_positions = inputs
        self._set_motors(motor_indexes, motor_positions)
    
    def set_shutter(self, inputs):
        shutter_state = inputs[0]
        error = self.api.set_shutter(shutter_state)
        self.shutter_position.write(shutter_state)
        return error
         
    def set_speed_parameters(self, inputs):
        motor_index, min_speed, max_speed, accelleration = inputs
        error = self.api._set_speed_parameters(motor_index, min_speed, max_speed, acceleration)
        return error
    
    def wait_until_still(self, inputs=[]):
        while self.is_busy():
            time.sleep(0.1)  # I've experienced hard crashes when wait set to 0.01 - Blaise 2015.12.30
            self.get_motor_positions()
        self.get_motor_positions()
    
    
def OPA_offline(OPA):
    
    def initialize(self):
        pass

    
### gui #######################################################################
    
    
class MotorControlGUI(QtGui.QWidget):
    
    def __init__(self, motor_name, motor_mutex, driver):
        QtGui.QWidget.__init__(self)
        self.motor_name = motor_name
        self.driver = driver
        self.layout = QtGui.QVBoxLayout()
        self.layout.setMargin(0)
        # table
        input_table = pw.InputTable()
        input_table.add(motor_name, motor_mutex)
        self.destination = motor_mutex.associate(display=False)
        input_table.add('Dest. ' + motor_name, self.destination)
        self.layout.addWidget(input_table)
        # buttons
        home_button, set_button = self.add_buttons(self.layout, 'HOME', 'advanced', 'SET', 'set')
        home_button.clicked.connect(self.on_home)
        set_button.clicked.connect(self.on_set)
        g.queue_control.disable_when_true(home_button)
        g.queue_control.disable_when_true(set_button)
        # finish
        self.setLayout(self.layout)
            
    def add_buttons(self, layout, button1_text, button1_color, button2_text, button2_color):
        colors = g.colors_dict.read()
        # layout
        button_container = QtGui.QWidget()
        button_container.setLayout(QtGui.QHBoxLayout())
        button_container.layout().setMargin(0)
        # button1
        button1 = QtGui.QPushButton()
        button1.setText(button1_text)
        button1.setMinimumHeight(25)
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors[button1_color])
        button1.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(button1)
        g.queue_control.disable_when_true(button1)
        # button2
        button2 = QtGui.QPushButton()
        button2.setText(button2_text)
        button2.setMinimumHeight(25)
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors[button2_color])
        button2.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(button2)
        g.queue_control.disable_when_true(button2)
        # finish
        layout.addWidget(button_container)
        return [button1, button2]
        
    def on_home(self):
        self.driver.address.hardware.q.push('home_motor', [self.motor_name])
    
    def on_set(self):
        destination = self.destination.read()
        self.driver.address.hardware.q.push('set_motor', [self.motor_name, destination])


class GUI(QtCore.QObject):

    def __init__(self, driver):
        QtCore.QObject.__init__(self)
        self.driver = driver

    def create_frame(self, layout):
        layout.setMargin(5)
        self.layout = layout
        self.frame = QtGui.QWidget()
        self.frame.setLayout(self.layout)
        if self.driver.initialized.read():
            self.initialize()
        else:
            self.driver.initialized.updated.connect(self.initialize)

    def initialize(self):
        # container widget
        display_container_widget = QtGui.QWidget()
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        self.layout.addWidget(display_container_widget)
        # plot
        self.plot_widget = pw.Plot1D()
        self.plot_widget.plot_object.setMouseEnabled(False, False)
        self.plot_curve = self.plot_widget.add_scatter()
        self.plot_h_line = self.plot_widget.add_infinite_line(angle=0, hide=False)
        self.plot_v_line = self.plot_widget.add_infinite_line(angle=90, hide=False)
        display_layout.addWidget(self.plot_widget)
        # vertical line
        line = pw.line('V')
        self.layout.addWidget(line)
        # container widget / scroll area
        settings_container_widget = QtGui.QWidget()
        settings_scroll_area = pw.scroll_area()
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        self.layout.addWidget(settings_scroll_area)
        # opa properties
        input_table = pw.InputTable()
        serial_number_display = pc.Number(initial_value=self.driver.serial_number, decimals=0, display=True)
        input_table.add('Serial Number', serial_number_display)
        settings_layout.addWidget(input_table)
        # plot control
        input_table = pw.InputTable()
        input_table.add('Display', None)
        self.plot_motor = pc.Combo(allowed_values=self.driver.curve.get_motor_names())
        self.plot_motor.updated.connect(self.update_plot)
        input_table.add('Motor', self.plot_motor)
        allowed_values = wt.units.energy.keys()
        allowed_values.remove('kind')
        self.plot_units = pc.Combo(initial_value='nm', allowed_values=allowed_values)
        self.plot_units.updated.connect(self.update_plot)
        input_table.add('Units', self.plot_units)
        settings_layout.addWidget(input_table)
        # curves
        input_table = pw.InputTable()
        input_table.add('Curves', None)
        for name, obj in self.driver.curve_paths.items():
            input_table.add(name, obj)
            obj.updated.connect(self.update_plot)
        input_table.add('Interaction String', self.driver.interaction_string_combo)
        self.low_energy_limit_display = pc.Number(units='nm', display=True)
        input_table.add('Low Energy Limit', self.low_energy_limit_display)
        self.high_energy_limit_display = pc.Number(units='nm', display=True)
        input_table.add('High Energy LImit', self.high_energy_limit_display)
        settings_layout.addWidget(input_table)
        self.driver.limits.updated.connect(self.on_limits_updated)
        # motors
        input_table = pw.InputTable()
        input_table.add('Motors', None)
        settings_layout.addWidget(input_table)
        for motor_name, motor_mutex in self.driver.motor_positions.items():
            settings_layout.addWidget(MotorControlGUI(motor_name, motor_mutex, self.driver))
        self.home_all_button = pw.SetButton('HOME ALL', 'advanced')
        settings_layout.addWidget(self.home_all_button)
        self.home_all_button.clicked.connect(self.on_home_all)
        g.queue_control.disable_when_true(self.home_all_button)
        # stretch
        settings_layout.addStretch(1)
        # signals and slots
        self.driver.interaction_string_combo.updated.connect(self.update_plot)
        self.driver.address.update_ui.connect(self.update)
        # finish
        self.update()
        self.update_plot()
        self.on_limits_updated()

    def update(self):
        print 'TOPAS update'
        # set button disable
        if self.driver.address.busy.read():
            self.home_all_button.setDisabled(True)
            for motor_mutex in self.driver.motor_positions.values():
                motor_mutex.set_disabled(True)
        else:
            self.home_all_button.setDisabled(False)
            for motor_mutex in self.driver.motor_positions.values():
                motor_mutex.set_disabled(False)
        # update destination motor positions
        # TODO: 
        # update plot lines
        motor_name = self.plot_motor.read()
        motor_position = self.driver.motor_positions[motor_name].read()
        self.plot_h_line.setValue(motor_position)
        units = self.plot_units.read()
        self.plot_v_line.setValue(self.driver.current_position.read(units))

    def update_plot(self):
        # units
        units = self.plot_units.read()
        # xi
        colors = self.driver.curve.colors
        xi = wt_units.converter(colors, 'nm', units)
        # yi
        self.plot_motor.set_allowed_values(self.driver.curve.get_motor_names())
        motor_name = self.plot_motor.read()
        motor_index = self.driver.curve.get_motor_names().index(motor_name)
        yi = self.driver.curve.get_motor_positions(colors, units)[motor_index]
        self.plot_widget.set_labels(xlabel=units, ylabel=motor_name)
        self.plot_curve.clear()
        self.plot_curve.setData(xi, yi)
        self.plot_widget.graphics_layout.update()
        self.update()

    def update_limits(self):
        if False:
            limits = self.opa.limits.read(self.opa.native_units)
            self.lower_limit.write(limits[0], self.opa.native_units)
            self.upper_limit.write(limits[1], self.opa.native_units)

    def on_home_all(self):
        self.driver.address.hardware.q.push('home_all')
        
    def on_limits_updated(self):
        low_energy_limit, high_energy_limit = self.driver.limits.read('wn')
        self.low_energy_limit_display.write(low_energy_limit, 'wn')
        self.high_energy_limit_display.write(high_energy_limit, 'wn')
        
    def show_advanced(self):
        pass

    def stop(self):
        pass



### testing ###################################################################


if __name__ == '__main__':
    
    if False:
        OPA1 = TOPAS(r'C:\Users\John\Desktop\PyCMDS\opas\TOPAS_C\configuration\10742.ini')
        print OPA1.set_shutter(False)
        print OPA1.get_motor_position(0)
        print OPA1.set_motor_position(0, 3478)
        print OPA1.get_motor_positions_range(0)
        # print OPA1._set_motor_offset
        # print OPA1._set_motor_affix
        # print OPA1._move_motor
        # print OPA1._move_motor_to_position_units
        print OPA1.set_motor_positions_range(0, 0, 9000)
        print OPA1.get_wavelength(0)
        print OPA1._get_motor_affix(0)
        print OPA1._get_device_serial_number()    
        print OPA1._is_wavelength_setting_finished()
        print OPA1.is_motor_still(0)
        print OPA1.get_reference_switch_status(0)
        print OPA1.get_count_of_motors(),
        print OPA1._get_count_of_devices()
        print OPA1.convert_position_to_units(0, 3000)
        print OPA1.convert_position_to_steps(0, -4.)
        print OPA1._get_speed_parameters(0)
        print OPA1.set_speed_parameters(0, 10, 600, 400)
        print OPA1._update_motors_positions()
        print OPA1._stop_motor(0)
        #print OPA1._start_setting_wavelength(1300.)
        #print OPA1._start_setting_wavelength_ex(1300., 0, 0, 0, 0)
        #print OPA1._set_wavelength(1300.)
        print OPA1.start_motor_motion(0, 4000) 
        #print OPA1._set_wavelength_ex(1300., 0, 0, 0, 0)
        #print OPA1.get_interaction(1)
        print OPA1.close()
        
        #log errors and handle them within the OPA object
        #make some convinient methods that are exposed higher up
        
    if False:
        topas = TOPAS(r'C:\Users\John\Desktop\PyCMDS\opas\TOPAS_C\configuration\10742.ini')
        print topas.set_shutter(False)
        with wt.kit.Timer():
            print topas.start_motor_motion(0, 1000)
            print topas.get_reference_switch_status(0)
        n = 0
        while not topas.are_all_motors_still()[1]:
            n += 1
            time.sleep(0.01)
            #topas._update_motors_positions()
            topas.get_motor_position(0)
            #time.sleep(1)
        print 'n =', n
        print topas.get_motor_position(0)
        print topas.are_all_motors_still()
        
        print topas.close()
        

### import ####################################################################


import os

import ctypes
from ctypes import *

import project.classes as pc
import project.project_globals as g
main_dir = g.main_dir.read()
                                 
                                 
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
              
              
### api object ################################################################


#IMPORTANT: THE WINDLL CALL MUST HAPPEN WITHIN THE TOPAS DRIVER FOLDER (os.chdir())

driver_folder = os.path.join(main_dir, 'hardware', 'opas', 'TOPAS', 'configuration', 'drivers')
os.chdir(driver_folder)
dll_path = os.path.join(driver_folder, 'TopasAPI.dll')
dll = ctypes.WinDLL(dll_path)
os.chdir(main_dir)

dll_busy = pc.Busy()

# NOTE: Cannot load more than 3 TOPAS OPAs (DLL restriction)
indicies = {}

class TOPAS_API():
    
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


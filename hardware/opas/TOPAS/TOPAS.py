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
from PyCMDS.hardware.opas import BaseOPA

import project.classes as pc
import project.widgets as pw
import project.project_globals as g
from project.ini_handler import Ini
main_dir = g.main_dir.read()
#ini = Ini(os.path.join(main_dir, 'hardware', 'opas',
#                                 'TOPAS_C',
#                                 'TOPAS.ini'))
                                 
                                 
### define ####################################################################
              
## TODO change curve_indices
## TODO make everything indices

### OPA object ################################################################


class TOPAS(BaseOPA):

    def __init__(self, motor_names=[], curve_indices={}, kind="TOPAS", has_shutter=False):
        super(TOPAS,self).__init__('nm')
        self.has_shutter = has_shutter
        self.curve_indices = curve_indices
        self.kind = kind
        if self.has_shutter:
            self.shutter_position = pc.Bool(name='Shutter',
                                            display=True, set_method='set_shutter')
            # objects to be sent to PyCMDS
            self.exposed += [self.shutter_position]
        self.motor_names = motor_names
        # finish
        self.auto_tune = AutoTune(self)
        self.homeable = [True]

    def TOPAS_800():
        motor_names = []
        curve_indices = {'Base': 1,
                          'Mixer 3': 4}
        kind = "TOPAS-800"
        return TOPAS(motor_names, curve_indices, kind, False)

    def TOPAS_C():
        motor_names = []
        curve_indices = {'Base': 1,
                          'Mixer 1': 2,
                          'Mixer 2': 3,
                          'Mixer 3': 4}
        kind = "TOPAS-C"
        return TOPAS(motor_names, curve_indices, kind, True)
        
    def _home_motors(self, motor_indexes):
        motor_indexes = list(motor_indexes)
        section = 'OPA' + str(self.index)
        # close shutter
        if self.has_shutter:
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
        if self.has_shutter:
            self.set_shutter([original_shutter])
        
    def _set_motors(self, motor_indexes, motor_destinations, wait=True):
        for motor_index, destination in zip(motor_indexes, motor_destinations):
            error, destination_steps = self.api.convert_position_to_steps(motor_index, destination)
            self.api.start_motor_motion(motor_index, destination_steps)
        if wait:
            self.wait_until_still()
        
    def close(self):
        if self.has_shutter:
            self.api.set_shutter(False)
        self.api.close()
    def _update_api(self, interaction):
        # write to TOPAS ini
        self.api.close()
        for curve_type, curve_path_mutex in self.curve_paths.items():
            curve_path = curve_path_mutex.read()            
            section = 'Optical Device'
            option = 'Curve ' + str(self.curve_indices[curve_type])
            self.TOPAS_ini.write(section, option, curve_path)
            print section, option, curve_path
        self.api = TOPAS(self.TOPAS_ini_filepath)
        # save current interaction string
        ini.write('OPA%i'%self.index, 'current interaction string', interaction)
    
    def _load_curve(self, inputs, interaction):
        ## TODO generalize crv_path curve loading
        crv_paths = [m.read() for m in self.curve_paths.values()]
        self.curve = wt.tuning.curve.from_TOPAS_crvs(crv_paths, self.kind, interaction)
        
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
        self.TOPAS_ini_filepath = os.path.join(g.main_dir.read(), 'hardware', 'opas', 'TOPAS', 'configuration', str(self.serial_number) + '.ini')
        self.api = TOPAS(self.TOPAS_ini_filepath)
        if self.has_shutter:
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
        for curve_type in self.curve_indices.keys():
            section = 'Optical Device'
            option = 'Curve ' + str(self.curve_indices[curve_type])
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
    
    def set_shutter(self, inputs):
        shutter_state = inputs[0]
        error = self.api.set_shutter(shutter_state)
        self.shutter_position.write(shutter_state)
        return error
         
    def set_speed_parameters(self, inputs):
        motor_index, min_speed, max_speed, accelleration = inputs
        error = self.api._set_speed_parameters(motor_index, min_speed, max_speed, acceleration)
        return error
    
### autotune ##################################################################


class TopasAutoTune(BaseOPAAutoTune):
    
    def __init__(self, opa):
        super(TopasAutoTune,self).__init__(opa)
        
    def initialize(self):
        input_table = pw.InputTable()
        self.operation_combo = pc.Combo()
        self.operation_combo.updated.connect(self.on_operation_changed)
        input_table.add('Operation', self.operation_combo)
        self.channel_combos = []
        self.layout.addWidget(input_table)
        # widgets
        self.widgets = collections.OrderedDict()
        # signal preamp -------------------------------------------------------
        w = pw.InputTable()
        # D1
        d1_width = pc.Number(initial_value=0.5)
        w.add('D1', None)
        w.add('Width', d1_width, key='D1 Width')
        d1_number = pc.Number(initial_value=51, decimals=0)
        w.add('Number', d1_number, key='D1 Number')
        channel = pc.Combo()
        self.channel_combos.append(channel)
        w.add('Channel', channel, key='D1 Channel')
        # test
        w.add('Test', None)
        do = pc.Bool(initial_value=True)
        w.add('Do', do)
        channel = pc.Combo()
        self.channel_combos.append(channel)
        w.add('Channel', channel, key='Test Channel')
        self.widgets['signal preamp'] = w
        self.layout.addWidget(w)
        # signal poweramp -----------------------------------------------------
        w = pw.InputTable()
        # D2
        w.add('D2', None)
        d2_width = pc.Number(initial_value=3.)
        w.add('D2 Width', d2_width)
        d2_number = pc.Number(initial_value=51, decimals=0)
        w.add('D2 Number', d2_number)
        channel = pc.Combo()
        self.channel_combos.append(channel)
        w.add('Channel', channel)
        # C2
        w.add('C2', None)
        c2_width = pc.Number(initial_value=2.)
        w.add('C2 Width', c2_width)
        c2_number = pc.Number(initial_value=51, decimals=0)
        w.add('C2 Number', c2_number)
        channel = pc.Combo()
        self.channel_combos.append(channel)
        w.add('Channel', channel)
        self.widgets['signal poweramp'] = w
        self.layout.addWidget(w)
        # SHS -----------------------------------------------------------------
        w = pw.InputTable()
        # M2
        w.add('M2', None)
        m2_width = pc.Number(initial_value=5.)
        w.add('M2 Width', m2_width)
        m2_number = pc.Number(initial_value=21, decimals=0)
        w.add('M2 Number', m2_number)
        channel = pc.Combo()
        self.channel_combos.append(channel)
        w.add('Channel', channel)
        # tune test
        w.add('Test', None)
        width = pc.Number(initial_value=-5000)
        w.add('Width', width)
        number = pc.Number(initial_value=51)
        w.add('Number', number)
        channel = pc.Combo()
        self.channel_combos.append(channel)
        w.add('Channel', channel)        
        self.widgets['SHS'] = w
        self.layout.addWidget(w)
        # finish --------------------------------------------------------------
        self.operation_combo.set_allowed_values(self.widgets.keys())
        # repetitions
        input_table = pw.InputTable()
        input_table.add('Repetitions', None)
        self.repetition_count = pc.Number(initial_value=1, decimals=0)
        input_table.add('Count', self.repetition_count)
        # finish
        self.layout.addWidget(input_table)
        self.initialized.write(True)
        self.on_operation_changed()
        
    def load(self, aqn_path):
        # TODO: channels
        aqn = wt.kit.INI(aqn_path)
        self.do_BBO.write(aqn.read('BBO', 'do'))
        self.BBO_width.write(aqn.read('BBO', 'width'))
        self.BBO_number.write(aqn.read('BBO', 'number'))
        self.do_Mixer.write(aqn.read('Mixer', 'do'))
        self.Mixer_width.write(aqn.read('Mixer', 'width'))
        self.Mixer_number.write(aqn.read('Mixer', 'number'))
        self.do_test.write(aqn.read('Test', 'do'))
        self.wm_width.write(aqn.read('Test', 'width'))
        self.wm_number.write(aqn.read('Test', 'number'))
        self.repetition_count.write(aqn.read('Repetitions', 'count'))
        
    def on_operation_changed(self):
        for w in self.widgets.values():
            w.hide()
        self.widgets[self.operation_combo.read()].show()
        
    def run(self, worker):
        import somatic.acquisition as acquisition
        # BBO -----------------------------------------------------------------
        if worker.aqn.read('BBO', 'do'):
            axes = []
            # tune points
            points = self.opa.curve.colors
            units = self.opa.curve.units
            name = identity = self.opa.address.hardware.friendly_name
            axis = acquisition.Axis(points=points, units=units, name=name, identity=identity)
            axes.append(axis)
            # motor
            name = '_'.join([self.opa.address.hardware.friendly_name, self.opa.curve.motor_names[1]])
            identity = 'D' + name
            width = worker.aqn.read('BBO', 'width') 
            npts = int(worker.aqn.read('BBO', 'number'))
            points = np.linspace(-width/2., width/2., npts)
            motor_positions = self.opa.curve.motors[1].positions
            kwargs = {'centers': motor_positions}
            hardware_dict = {name: [self.opa.address.hardware, 'set_motor', ['BBO', 'destination']]}
            axis = acquisition.Axis(points, None, name, identity, hardware_dict, **kwargs)
            axes.append(axis)
            # do scan
            scan_folder = worker.scan(axes)
            # process
            p = os.path.join(scan_folder, '000.data')
            data = wt.data.from_PyCMDS(p)
            curve = self.opa.curve
            channel = worker.aqn.read('BBO', 'channel')
            old_curve_filepath = self.opa.curve_path.read()
            wt.tuning.workup.intensity(data, curve, channel, save_directory=scan_folder)
            # apply new curve
            p = wt.kit.glob_handler('.curve', folder=scan_folder)[0]
            self.opa.curve_path.write(p)
            # upload
            p = wt.kit.glob_handler('.png', folder=scan_folder)[0]
            worker.upload(scan_folder, reference_image=p)
        # Mixer ---------------------------------------------------------------
        if worker.aqn.read('Mixer', 'do'):
            axes = []
            # tune points
            points = self.opa.curve.colors
            units = self.opa.curve.units
            name = identity = self.opa.address.hardware.friendly_name
            axis = acquisition.Axis(points=points, units=units, name=name, identity=identity)
            axes.append(axis)
            # motor
            name = '_'.join([self.opa.address.hardware.friendly_name, self.opa.curve.motor_names[2]])
            identity = 'D' + name
            width = worker.aqn.read('Mixer', 'width') 
            npts = int(worker.aqn.read('Mixer', 'number'))
            points = np.linspace(-width/2., width/2., npts)
            motor_positions = self.opa.curve.motors[2].positions
            kwargs = {'centers': motor_positions}
            hardware_dict = {name: [self.opa.address.hardware, 'set_motor', ['Mixer', 'destination']]}
            axis = acquisition.Axis(points, None, name, identity, hardware_dict, **kwargs)
            axes.append(axis)
            # do scan
            scan_folder = worker.scan(axes)
            # process
            p = os.path.join(scan_folder, '000.data')
            data = wt.data.from_PyCMDS(p)
            curve = self.opa.curve
            channel = worker.aqn.read('Mixer', 'channel')
            old_curve_filepath = self.opa.curve_path.read()
            wt.tuning.workup.intensity(data, curve, channel, save_directory=scan_folder)
            # apply new curve
            p = wt.kit.glob_handler('.curve', folder=scan_folder)[0]
            self.opa.curve_path.write(p)
            # upload
            p = wt.kit.glob_handler('.png', folder=scan_folder)[0]
            worker.upload(scan_folder, reference_image=p)
        # Tune Test -----------------------------------------------------------
        if worker.aqn.read('Test', 'do'):
            axes = []
            # tune points
            points = self.opa.curve.colors
            units = self.opa.curve.units
            name = identity = self.opa.address.hardware.friendly_name
            axis = acquisition.Axis(points=points, units=units, name=name, identity=identity)
            axes.append(axis)
            # mono
            name = 'wm'
            identity = 'Dwm'
            width = worker.aqn.read('Test', 'width') 
            npts = int(worker.aqn.read('Test', 'number'))
            points = np.linspace(-width/2., width/2., npts)
            kwargs = {'centers': self.opa.curve.colors}
            axis = acquisition.Axis(points, 'wn', name, identity, **kwargs)
            axes.append(axis)
            # do scan
            scan_folder = worker.scan(axes)
            # process
            p = wt.kit.glob_handler('.data', folder=scan_folder)[0]
            data = wt.data.from_PyCMDS(p)
            curve = self.opa.curve
            channel = worker.aqn.read('Test', 'channel')
            wt.tuning.workup.tune_test(data, curve, channel, save_directory=scan_folder)
            # apply new curve
            p = wt.kit.glob_handler('.curve', folder=scan_folder)[0]
            self.opa.curve_path.write(p)
            # upload
            p = wt.kit.glob_handler('.png', folder=scan_folder)[0]
            worker.upload(scan_folder, reference_image=p)
        # finish --------------------------------------------------------------
        # return to old curve
        # TODO:
        if not worker.stopped.read():
            worker.finished.write(True)  # only if acquisition successfull
    
    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        operation = self.operation_combo.read()
        description = ' '.join(['OPA%i'%self.opa.index, operation])
        aqn.write('info', 'description', description)
        w = self.widgets[operation]
        if operation == 'signal preamp':
            aqn.add_section('D1')
            aqn.write('D1', 'width', w['D1 Width'].read())
        elif operation == 'signal poweramp':
            # TODO:
            raise NotImplementedError
        elif operation == 'SHS':
            # TODO:
            raise NotImplementedError
        else:
            raise Exception('operation {0} not recognized'.format(operation))


        
    def update_channel_names(self, channel_names):
        for c in self.channel_combos:
            c.set_allowed_values(channel_names)


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
        

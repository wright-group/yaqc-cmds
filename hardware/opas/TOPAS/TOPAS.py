# --- import --------------------------------------------------------------------------------------


import os
import time
import copy
import collections

import numpy as np

import ctypes
from ctypes import *

import WrightTools as wt
import attune

import project
import project.classes as pc
import project.widgets as pw
import project.project_globals as g
from project.ini_handler import Ini
from hardware.opas.opas import Driver as BaseDriver
from hardware.opas.opas import GUI as BaseGUI
from hardware.opas.opas import AutoTune as BaseAutoTune
from hardware.opas.TOPAS.TOPAS_API import TOPAS_API
from attune.curve._topas import TOPAS_interaction_by_kind
                                 
# --- define --------------------------------------------------------------------------------------


main_dir = g.main_dir.read()


# --- autotune ------------------------------------------------------------------------------------


class AutoTune(BaseAutoTune):

    def initialize(self):
        input_table = pw.InputTable()
        self.operation_combo = pc.Combo()
        self.operation_combo.updated.connect(self.on_operation_changed)
        input_table.add('Operation', self.operation_combo)
        self.channel_combos = []
        self.layout.addWidget(input_table)
        # widgets
        self.widgets = collections.OrderedDict()
        # signal preamp ---------------------------------------------------------------------------
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
        # signal poweramp -------------------------------------------------------------------------
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
        # SHS -------------------------------------------------------------------------------------
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
        # finish ----------------------------------------------------------------------------------
        self.operation_combo.set_allowed_values(list(self.widgets.keys()))
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
        curve = self.opa.curve
        while not curve.kind.startswith('TOPAS'):
            curve = curve.subcurve
        # BBO -------------------------------------------------------------------------------------
        if worker.aqn.read('BBO', 'do'):
            axes = []
            # tune points
            points = curve.colors
            units = curve.units
            name = identity = self.opa.hardware.name
            axis = acquisition.Axis(points=points, units=units, name=name, identity=identity)
            axes.append(axis)
            # motor
            name = '_'.join([name, curve.motor_names[1]])
            identity = 'D' + name
            width = worker.aqn.read('BBO', 'width') 
            npts = int(worker.aqn.read('BBO', 'number'))
            points = np.linspace(-width/2., width/2., npts)
            motor_positions = curve.motors[1].positions
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
            old_curve_filepath = curve_path.read()
            transform = list(data.axis_names)
            transform[-1] = transform[-1] + "_points"
            data.transform(*transform)
            attune.workup.intensity(data, curve, channel, save_directory=scan_folder)
            # apply new curve
            p = wt.kit.glob_handler('.curve', folder=scan_folder)[0]
            self.opa.curve_path.write(p)
            # upload
            p = wt.kit.glob_handler('.png', folder=scan_folder)[0]
            worker.upload(scan_folder, reference_image=p)
        # Mixer -----------------------------------------------------------------------------------
        if worker.aqn.read('Mixer', 'do'):
            axes = []
            # tune points
            points = curve.colors
            units = curve.units
            name = identity = self.opa.hardware.name
            axis = acquisition.Axis(points=points, units=units, name=name, identity=identity)
            axes.append(axis)
            # motor
            name = '_'.join([name, curve.motor_names[2]])
            identity = 'D' + name
            width = worker.aqn.read('Mixer', 'width') 
            npts = int(worker.aqn.read('Mixer', 'number'))
            points = np.linspace(-width/2., width/2., npts)
            motor_positions = curve.motors[2].positions
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
            transform = list(data.axis_names)
            transform[-1] = transform[-1] + "_points"
            data.transform(*transform)
            attune.workup.intensity(data, curve, channel, save_directory=scan_folder)
            # apply new curve
            p = wt.kit.glob_handler('.curve', folder=scan_folder)[0]
            self.opa.curve_path.write(p)
            # upload
            p = wt.kit.glob_handler('.png', folder=scan_folder)[0]
            worker.upload(scan_folder, reference_image=p)
        # Tune Test -------------------------------------------------------------------------------
        if worker.aqn.read('Test', 'do'):
            axes = []
            # tune points
            points = curve.colors
            units = curve.units
            name = identity = self.opa.hardware.name
            axis = acquisition.Axis(points=points, units=units, name=name, identity=identity)
            axes.append(axis)
            # mono
            name = 'wm'
            identity = 'Dwm'
            width = worker.aqn.read('Test', 'width') 
            npts = int(worker.aqn.read('Test', 'number'))
            points = np.linspace(-width/2., width/2., npts)
            kwargs = {'centers': curve.colors}
            axis = acquisition.Axis(points, 'wn', name, identity, **kwargs)
            axes.append(axis)
            # do scan
            scan_folder = worker.scan(axes)
            # process
            p = wt.kit.glob_handler('.data', folder=scan_folder)[0]
            data = wt.data.from_PyCMDS(p)
            curve = self.opa.curve
            channel = worker.aqn.read('Test', 'channel')
            transform = list(data.axis_names)
            transform[-1] = transform[-1] + "_points"
            data.transform(*transform)
            attune.workup.tune_test(data, curve, channel, save_directory=scan_folder)
            # apply new curve
            p = wt.kit.glob_handler('.curve', folder=scan_folder)[0]
            self.opa.curve_path.write(p)
            # upload
            p = wt.kit.glob_handler('.png', folder=scan_folder)[0]
            worker.upload(scan_folder, reference_image=p)
        # finish ----------------------------------------------------------------------------------
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


# --- driver --------------------------------------------------------------------------------------


class Driver(BaseDriver):

    def __init__(self, *args, **kwargs):
        self.auto_tune = AutoTune(self)
        self.motors=[]
        self.curve_paths = collections.OrderedDict()
        self.ini = project.ini_handler.Ini(os.path.join(main_dir, 'hardware', 'opas', 'TOPAS', 'TOPAS.ini'))
        self.has_shutter = kwargs['has_shutter']
        if self.has_shutter:
            self.shutter_position = pc.Bool(name='Shutter', display=True, set_method='set_shutter')
        allowed_values = list(TOPAS_interaction_by_kind[self.kind].keys())
        self.interaction_string_combo = pc.Combo(allowed_values = allowed_values)
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
        allowed_values = []
        for curve_path_mutex in self.curve_paths.values():
            with open(curve_path_mutex.read()) as crv:
                crv_lines = crv.readlines()
            for line in crv_lines:
                if 'NON' in line:
                    allowed_values.append(line.rstrip())
        self.interaction_string_combo = pc.Combo(allowed_values=allowed_values)
        current_value = self.ini.read('OPA%i'%self.index, 'current interaction string')
        self.interaction_string_combo.write(current_value)
        self.interaction_string_combo.updated.connect(self.load_curve)
        g.queue_control.disable_when_true(self.interaction_string_combo)
        self.load_curve(update = False)

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
        print(curve_paths_copy)
        if 'Poynting' in curve_paths_copy.keys():
            del curve_paths_copy['Poynting']
        print(self.curve_paths)
        crv_paths = [m.read() for m in curve_paths_copy.values()]
        used = list(self.curve_indices.values())
        need = [x for x in range(4) if x+1 not in used]        
        for i in need:
            crv_paths.insert(i,None)
        self.curve = attune.curve.read_topas(crv_paths, self.kind, interaction)
        return self.curve
       
    def _set_motors(self, motor_indexes, motor_destinations):
        for motor_index, destination in zip(motor_indexes, motor_destinations):
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
        #self.get_motor_positions()
        # set position
        position = self.ini.read('OPA%i'%self.index, 'position (nm)')
        self.hardware.destination.write(position, self.native_units)
        #self.set_position(position) #TODO make sure set position is handled in the base class
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

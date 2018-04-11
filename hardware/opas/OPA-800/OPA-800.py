### import ####################################################################

import os
import collections

import numpy as np

import WrightTools as wt

import project.classes as pc
import project.widgets as pw
import project.project_globals as g
from hardware.opas.opas import Driver as BaseDriver
from hardware.opas.opas import GUI as BaseGUI
from hardware.opas.opas import AutoTune as BaseAutoTune
import library.precision_micro_motors.precision_motors as pm_motors


### define ####################################################################


main_dir = g.main_dir.read()


### autotune ##################################################################


class AutoTune(BaseAutoTune):

    def initialize(self):
        input_table = pw.InputTable()
        # BBO
        input_table.add('BBO', None)
        self.do_BBO = pc.Bool(initial_value=True)
        input_table.add('Do', self.do_BBO)
        self.BBO_width = pc.Number(initial_value=0.75)
        input_table.add('Width', self.BBO_width)
        self.BBO_number = pc.Number(initial_value=25, decimals=0)
        input_table.add('Number', self.BBO_number)
        self.BBO_channel = pc.Combo()
        input_table.add('Channel', self.BBO_channel)
        # Mixer
        input_table.add('Mixer', None)
        self.do_Mixer = pc.Bool(initial_value=True)
        input_table.add('Do', self.do_Mixer)
        self.Mixer_width = pc.Number(initial_value=0.5)
        input_table.add('Width', self.Mixer_width)
        self.Mixer_number = pc.Number(initial_value=25, decimals=0)
        input_table.add('Number', self.Mixer_number)
        self.Mixer_channel = pc.Combo()
        input_table.add('Channel', self.Mixer_channel)
        # Tune test
        input_table.add('Test', None)
        self.do_test = pc.Bool(initial_value=True)
        input_table.add('Do', self.do_test)
        self.wm_width = pc.Number(initial_value=-200)
        input_table.add('Width', self.wm_width)
        self.wm_number = pc.Number(initial_value=41, decimals=0)
        input_table.add('Number', self.wm_number)
        self.test_channel = pc.Combo()
        input_table.add('Channel', self.test_channel)
        # repetitions
        input_table.add('Repetitions', None)
        self.repetition_count = pc.Number(initial_value=1, decimals=0)
        input_table.add('Count', self.repetition_count)
        # finish
        self.layout.addWidget(input_table)
        self.initialized.write(True)

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

    def run(self, worker):
        import somatic.acquisition as acquisition
        curve = self.driver.curve
        while curve.kind != 'opa800':
            curve = curve.subcurve

        # BBO -----------------------------------------------------------------
        if worker.aqn.read('BBO', 'do'):
            axes = []
            # tune points
            points = curve.colors
            units = curve.units
            name = identity = self.driver.name
            axis = acquisition.Axis(points=points, units=units, name=name, identity=identity)
            axes.append(axis)
            # motor
            name = '_'.join([self.driver.name, curve.motor_names[1]])
            identity = 'D' + name
            width = worker.aqn.read('BBO', 'width')
            npts = int(worker.aqn.read('BBO', 'number'))
            points = np.linspace(-width/2., width/2., npts)
            motor_positions = curve.motors[1].positions
            kwargs = {'centers': motor_positions}
            hardware_dict = {name: [self.driver.hardware, 'set_motor', ['BBO', 'destination']]}
            axis = acquisition.Axis(points, None, name, identity, hardware_dict, **kwargs)
            axes.append(axis)
            # do scan
            scan_folder = worker.scan(axes)
            # process
            p = os.path.join(scan_folder, '000.data')
            data = wt.data.from_PyCMDS(p)
            channel = worker.aqn.read('BBO', 'channel')
            wt.tuning.workup.intensity(data, curve, channel, save_directory=scan_folder)
            # apply new curve
            p = wt.kit.glob_handler('.curve', folder=scan_folder)[0]
            self.driver.curve_path.write(p)
            # upload
            p = wt.kit.glob_handler('.png', folder=scan_folder)[0]
            worker.upload(scan_folder, reference_image=p)
        # Mixer ---------------------------------------------------------------
        if worker.aqn.read('Mixer', 'do'):
            axes = []
            # tune points
            points = curve.colors
            units = curve.units
            name = identity = self.driver.name
            axis = acquisition.Axis(points=points, units=units, name=name, identity=identity)
            axes.append(axis)
            # motor
            name = '_'.join([self.driver.name, curve.motor_names[2]])
            identity = 'D' + name
            width = worker.aqn.read('Mixer', 'width')
            npts = int(worker.aqn.read('Mixer', 'number'))
            points = np.linspace(-width/2., width/2., npts)
            motor_positions = curve.motors[2].positions
            kwargs = {'centers': motor_positions}
            hardware_dict = {name: [self.driver.hardware, 'set_motor', ['Mixer', 'destination']]}
            axis = acquisition.Axis(points, None, name, identity, hardware_dict, **kwargs)
            axes.append(axis)
            # do scan
            scan_folder = worker.scan(axes)
            # process
            p = os.path.join(scan_folder, '000.data')
            data = wt.data.from_PyCMDS(p)
            channel = worker.aqn.read('Mixer', 'channel')
            wt.tuning.workup.intensity(data, curve, channel, save_directory=scan_folder)
            # apply new curve
            p = wt.kit.glob_handler('.curve', folder=scan_folder)[0]
            self.driver.curve_path.write(p)
            # upload
            p = wt.kit.glob_handler('.png', folder=scan_folder)[0]
            worker.upload(scan_folder, reference_image=p)
        # Tune Test -----------------------------------------------------------
        if worker.aqn.read('Test', 'do'):
            axes = []
            # tune points
            points = curve.colors
            units = curve.units
            name = identity = self.driver.name
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
            channel = worker.aqn.read('Test', 'channel')
            wt.tuning.workup.tune_test(data, curve, channel, save_directory=scan_folder)
            # apply new curve
            p = wt.kit.glob_handler('.curve', folder=scan_folder)[0]
            self.driver.curve_path.write(p)
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
        aqn.add_section('BBO')
        aqn.write('BBO', 'do', self.do_BBO.read())
        aqn.write('BBO', 'width', self.BBO_width.read())
        aqn.write('BBO', 'number', self.BBO_number.read())
        aqn.write('BBO', 'channel', self.BBO_channel.read())
        aqn.add_section('Mixer')
        aqn.write('Mixer', 'do', self.do_Mixer.read())
        aqn.write('Mixer', 'width', self.Mixer_width.read())
        aqn.write('Mixer', 'number', self.Mixer_number.read())
        aqn.write('Mixer', 'channel', self.Mixer_channel.read())
        aqn.add_section('Test')
        aqn.write('Test', 'do', self.do_test.read())
        aqn.write('Test', 'width', self.wm_width.read())
        aqn.write('Test', 'number', self.wm_number.read())
        aqn.write('Test', 'channel', self.test_channel.read())
        aqn.add_section('Repetitions')
        aqn.write('Repetitions', 'count', self.repetition_count.read())

    def update_channel_names(self, channel_names):
        self.BBO_channel.set_allowed_values(channel_names)
        self.Mixer_channel.set_allowed_values(channel_names)
        self.test_channel.set_allowed_values(channel_names)


### driver ####################################################################


class Driver(BaseDriver):

    def __init__(self, *args, **kwargs):
        self.motor_names = ['Grating', 'BBO', 'Mixer']
        self.auto_tune = AutoTune(self)
        self.motors = []
        self.homeable = [False]
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
        print(self.curve_paths)
        self.load_curve()

    def _load_curve(self, interaction):
        '''
        when loading externally, write to curve_path object directly
        '''
        self.curve = wt.tuning.curve.from_800_curve(self.curve_paths['Curve'].read())
        return self.curve

    def _set_motors(self, motor_indexes, motor_destinations):
        for axis, dest in zip(motor_indexes, motor_destinations):
            if axis < 3:
                if dest >= 0 and dest <= 50:
                    self.motors[axis].move_absolute(dest)
                else:
                    print('That is not a valid axis '+str(axis)+' motor positon. Nice try, bucko.')
            else:
                print('Unrecognized axis '+str(axis))

    def _wait_until_still(self):
        for motor in self.motors:
            motor.wait_until_still(method=self.get_position)

    def close(self):
        for motor in self.motors:
            motor.close()
        BaseDriver.close(self)

    def get_motor_positions(self):
        for i in range(len(self.motors)):
            val = self.motors[i].current_position_mm
            list(self.motor_positions.values())[i].write(val)
        if self.poynting_correction:
            self.poynting_correction.get_motor_positions()

    def initialize(self):
        self.hardware.destination.write(self.position.read(self.native_units), self.native_units)
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
            self.motors.append(pm_motors.Motor(
                pm_motors.identity['OPA%d %s' % (self.index, motor_name)]))
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
        for motor in self.motors:
            if not motor.is_stopped():
                self.get_position()
                return True
        self.get_position()
        return False


### gui #######################################################################


class GUI(BaseGUI):
    pass

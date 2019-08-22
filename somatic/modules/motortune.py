### import ####################################################################


import os
import pathlib

import numpy as np

import matplotlib
matplotlib.pyplot.ioff()

import WrightTools as wt

import project.project_globals as g
import project.classes as pc
import project.widgets as pw
import somatic.acquisition as acquisition
import project.ini_handler as ini_handler
main_dir = g.main_dir.read()
ini = ini_handler.Ini(os.path.join(main_dir, 'somatic', 'modules', 'motortune.ini'))
app = g.app.read()

import hardware.opas.opas as opas
import hardware.spectrometers.spectrometers as spectrometers
import devices.devices as devices

 
### define ####################################################################


module_name = 'MOTORTUNE'


### custom classes ############################################################


class MotorGUI():
    
    def __init__(self, name, center, width, number, use_tune_points):
        self.name = name
        self.use_tune_points = use_tune_points
        self.input_table = pw.InputTable()
        self.input_table.add(name, None)
        allowed = ['Set', 'Scan', 'Static']
        self.method = pc.Combo(allowed_values=allowed)
        if self.use_tune_points is not None:
            self.use_tune_points.updated.connect(self.update_disabled)
        self.method.updated.connect(self.update_disabled)
        self.input_table.add('Method', self.method)
        self.center = pc.Number(initial_value=center)
        self.input_table.add('Center', self.center)
        self.width = pc.Number(initial_value=width)
        self.input_table.add('Width', self.width)
        self.npts = pc.Number(initial_value=number, decimals=0)
        self.input_table.add('Number', self.npts)
        self.update_disabled()

    def update_disabled(self):
        self.center.set_disabled(True)
        self.width.set_disabled(True)
        self.npts.set_disabled(True)
        method = self.method.read()
        if method == 'Set':
            self.center.set_disabled(self.use_tune_points.read())
        elif method == 'Scan':
            self.center.set_disabled(self.use_tune_points.read())
            self.width.set_disabled(False)
            self.npts.set_disabled(False)
        elif method == 'Static':
            self.center.set_disabled(False)


class OPA_GUI():
    
    def __init__(self, hardware, layout, use_tune_points):
        self.hardware = hardware
        motor_names = self.hardware.motor_names
        self.motors = []
        for name in motor_names:
            motor = MotorGUI(name, 30, 1, 11, use_tune_points)
            if layout is not None:
                layout.addWidget(motor.input_table)
            self.motors.append(motor)
        self.hide()  # initialize hidden
            
    def hide(self):
        for motor in self.motors:
            motor.input_table.hide()
    
    def show(self):
        for motor in self.motors:
            motor.input_table.show()


 
### Worker ####################################################################


class Worker(acquisition.Worker):
    
    def process(self, scan_folder):
        if not self.aqn.read('processing', 'do post process'):
            self.upload(self.scan_folders[self.scan_index], reference_image=None)
            return
        # get path
        data_path = devices.data_path.read() 
        # make data object
        data = wt.data.from_PyCMDS(data_path, verbose=False)
        data_path = pathlib.Path(data_path)
        data_folder = data_path.parent
        ouput_folder = data_folder
        channel_path = data_folder / channel
        if data.ndim > 2:
            output_folder = channel_path
            channel_path.mkdir()
        file_name = data_path.stem
        file_extension = data_path.suffix
        # make all images
        channel = self.aqn.read('processing', 'channel')
        image_fname = channel
        if data.ndim == 1:
            filepaths = wt.artists.quick1D(data, channel=channel, autosave=True, save_directory=output_folder,
                        fname=image_fname, verbose=False)
        else:
            filepaths = wt.artists.quick2D(data, -1, -2, channel=channel, autosave=True, save_directory=output_folder,
                        fname=image_fname, verbose=False)
        # get output image
        if len(filepaths) == 1:
            output_image_path = filepaths[0]
        else:
            output_image_path = str(output_folder / 'animation.gif')
            wt.artists.stitch_to_animation(images=filepaths, outpath=output_image_path)
        # upload
        self.upload(self.scan_folders[self.scan_index], reference_image=output_image_path)    
    
    def run(self):
        # assemble axes
        axes = []
        # get OPA properties
        opa_name = self.aqn.read('motortune', 'opa name')
        opa_names = [h.name for h in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        opa_hardware = opas.hardwares[opa_index]
        opa_friendly_name = opa_hardware.name
        curve = opa_hardware.curve
        motor_names = self.aqn.read('motortune', 'motor names')
        # tune points        
        if self.aqn.read('motortune', 'use tune points'):
            motors_excepted = []  # list of indicies  
            for motor_name in motor_names:
                if not self.aqn.read(motor_name, 'method') == 'Set':
                    motors_excepted.append(motor_name)
            if self.aqn.read('spectrometer', 'method') == 'Set':
                identity = opa_friendly_name + '=wm'
                hardware_dict = {opa_friendly_name: [opa_hardware, 'set_position_except', ['destination', motors_excepted]],
                                 'wm': [spectrometers.hardwares[0], 'set_position', None]}
                axis = acquisition.Axis(curve.setpoints[:], curve.setpoints.units, opa_friendly_name, identity, hardware_dict)
                axes.append(axis)
            else:
                hardware_dict = {opa_friendly_name: [opa_hardware, 'set_position_except', ['destination', motors_excepted]]}
                axis = acquisition.Axis(curve.setpoints[:], curve.setpoints.units, opa_friendly_name, opa_friendly_name, hardware_dict)
                axes.append(axis)
        # motor
        for motor_name in motor_names:
            if self.aqn.read(motor_name, 'method') == 'Scan':
                motor_units = None
                name = '_'.join([opa_friendly_name, motor_name])
                width = self.aqn.read(motor_name, 'width')/2.
                npts = self.aqn.read(motor_name, 'number')
                if self.aqn.read('motortune', 'use tune points'):
                    center = 0.
                    identity = 'D'+name
                    motor_positions = curve[motor_name][:]
                    kwargs = {'centers': motor_positions}
                else:
                    center = self.aqn.read(motor_name, 'center')
                    identity = name
                    kwargs = {}
                points = np.linspace(center-width, center+width, npts)
                hardware_dict = {name: [opa_hardware, 'set_motor', [motor_name, 'destination']]}
                axis = acquisition.Axis(points, motor_units, name, identity, hardware_dict, **kwargs)
                axes.append(axis)
            elif self.aqn.read(motor_name, 'method') == 'Set':
                pass
            elif self.aqn.read(motor_name, 'method') == 'Static':
                opa_hardware.q.push('set_motor', [motor_name, self.aqn.read(motor_name, 'center')])
        # mono
        if self.aqn.read('spectrometer', 'method') == 'Scan':
            name = 'wm'
            units = 'wn'
            width = self.aqn.read('spectrometer', 'width')/2.
            npts = self.aqn.read('spectrometer', 'number')
            if self.aqn.read('motortune', 'use tune points'):
                center = 0.
                identity = 'D'+name
                curve = curve.copy()
                curve.convert('wn')
                #centers_shape = [a.points.size for a in axes]
                #centers = np.transpose(curve.setpoints[:] * np.ones(centers_shape).T)
                kwargs = {'centers': curve.setpoints[:]}
            else:
                center = self.aqn.read('spectrometer', 'center')
                center = wt.units.convert(center, self.aqn.read('spectrometer', 'center units'), 'wn')
                identity = name
                kwargs = {}
            points = np.linspace(center-width, center+width, npts)
            axis = acquisition.Axis(points, units, name, identity, **kwargs)
            axes.append(axis)
        elif self.aqn.read('spectrometer', 'method') == 'Set':
            if self.aqn.read('motortune', 'use tune points'):
                # already handled above
                pass
            else:
                center = self.aqn.read('spectrometer', 'center')
                center = wt.units.convert(center, self.aqn.read('spectrometer', 'center units'), 'wn')              
                spectrometers.hardwares[0].set_position(center, 'wn')
        elif self.aqn.read('spectrometer', 'method') == 'Static':
            center = self.aqn.read('spectrometer', 'center')
            center = wt.units.convert(center, self.aqn.read('spectrometer', 'center units'), 'wn')
            spectrometers.hardwares[0].set_position(center, 'wn')
        # handle centers
        for axis_index, axis in enumerate(axes):
            centers_shape = [a.points.size for i, a in enumerate(axes) if not i == axis_index]
            ones = np.ones(centers_shape)
            if hasattr(axis, 'centers'):
                # arrays always follow
                axis.centers = np.transpose(axis.centers * ones.T)
        # launch
        pre_wait_methods = [lambda: opa_hardware.q.push('wait_until_still'),
                            lambda: opa_hardware.q.push('get_motor_positions'),
                            lambda: opa_hardware.q.push('get_position')]
        # do scan
        self.scan(axes, constants=[], pre_wait_methods=pre_wait_methods)
        if not self.stopped.read():
            self.finished.write(True)  # only if acquisition successfull


### GUI #######################################################################


class GUI(acquisition.GUI):

    def create_frame(self):
        # shared settings
        input_table = pw.InputTable()
        allowed = [hardware.name for hardware in opas.hardwares]
        self.opa_combo = pc.Combo(allowed)
        input_table.add('OPA', self.opa_combo)
        self.opa_combo.updated.connect(self.on_opa_combo_updated)
        self.use_tune_points = pc.Bool(initial_value=True)
        input_table.add('Use Tune Points', self.use_tune_points)
        self.layout.addWidget(input_table)
        # motor settings
        self.opa_guis = [OPA_GUI(hardware, self.layout, self.use_tune_points) for hardware in opas.hardwares]
        self.opa_guis[0].show()
        # mono settings
        allowed = ['Set', 'Scan', 'Static']
        self.mono_method_combo = pc.Combo(allowed, disable_under_module_control=True)
        self.mono_method_combo.updated.connect(self.update_mono_settings)
        self.mono_center = pc.Number(initial_value=7000, units='wn', disable_under_module_control=True)
        self.mono_width = pc.Number(initial_value=500, units='wn', disable_under_module_control=True)
        self.mono_width.set_disabled_units(True)
        self.mono_npts = pc.Number(initial_value=51, decimals=0, disable_under_module_control=True)
        input_table = pw.InputTable()
        input_table.add('Spectrometer', None)
        input_table.add('Method', self.mono_method_combo)
        input_table.add('Center', self.mono_center)
        input_table.add('Width', self.mono_width)
        input_table.add('Number', self.mono_npts)
        self.layout.addWidget(input_table)
        self.update_mono_settings()
        # processing
        input_table = pw.InputTable()
        input_table.add('Processing', None)
        self.do_post_process = pc.Bool(initial_value=True)
        input_table.add('Process', self.do_post_process)
        # TODO: allowed values, update
        self.main_channel = pc.Combo()
        input_table.add('Channel', self.main_channel)
        self.layout.addWidget(input_table)        
        
    def load(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        # shared settings
        self.opa_combo.write(aqn.read('motortune', 'opa name'))
        self.use_tune_points.write(aqn.read('motortune', 'use tune points'))
        # motor settings
        opa = self.opa_guis[self.opa_combo.read_index()]
        for motor, motor_name in zip(opa.motors, aqn.read('motortune', 'motor names')):
            motor.method.write(aqn.read(motor_name, 'method'))
            motor.center.write(aqn.read(motor_name, 'center'))
            motor.width.write(aqn.read(motor_name, 'width'))
            motor.npts.write(aqn.read(motor_name, 'number'))
        # mono settings
        self.mono_method_combo.write(aqn.read('spectrometer', 'method'))
        self.mono_center.write(aqn.read('spectrometer', 'center'))
        self.mono_width.write(aqn.read('spectrometer', 'width'))
        self.mono_npts.write(aqn.read('spectrometer', 'number'))
        # processing
        self.do_post_process.write(aqn.read('processing', 'do post process'))
        self.main_channel.write(aqn.read('processing', 'channel'))
        # allow devices to read from aqn
        self.device_widget.load(aqn_path)
    
    def on_device_settings_updated(self):
        self.main_channel.set_allowed_values(devices.control.channel_names)
    
    def on_opa_combo_updated(self):
        self.show_opa_gui(self.opa_combo.read_index())
        
    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        opa = self.opa_guis[self.opa_combo.read_index()]
        scanned_motor_names = []
        for motor in opa.motors:
            if motor.method == 'Scan':
                scanned_motor_names.append(motor.name)
        scanned_motor_names = str(scanned_motor_names).replace('\'', '')
        aqn.write('info', 'description', 'MOTORTUNE: {} {}'.format(self.opa_combo.read(), scanned_motor_names))
        # shared settings
        aqn.add_section('motortune')
        aqn.write('motortune', 'opa name', self.opa_combo.read())
        aqn.write('motortune', 'motor names', [motor.name for motor in self.opa_guis[self.opa_combo.read_index()].motors])
        aqn.write('motortune', 'use tune points', self.use_tune_points.read())
        # motor settings
        for motor in opa.motors:
            aqn.add_section(motor.name)
            aqn.write(motor.name, 'method', motor.method.read())
            aqn.write(motor.name, 'center', motor.center.read())
            aqn.write(motor.name, 'width', motor.width.read())
            aqn.write(motor.name, 'number', motor.npts.read())
        # mono settings
        aqn.add_section('spectrometer')
        aqn.write('spectrometer', 'method', self.mono_method_combo.read())
        aqn.write('spectrometer', 'center', self.mono_center.read())
        aqn.write('spectrometer', 'center units', self.mono_center.units)
        aqn.write('spectrometer', 'width', self.mono_width.read())
        aqn.write('spectrometer', 'number', self.mono_npts.read())
        # processing
        aqn.add_section('processing')
        aqn.write('processing', 'do post process', self.do_post_process.read())
        aqn.write('processing', 'channel', self.main_channel.read())
        # allow devices to save to aqn
        self.device_widget.save(aqn_path)
        
    def show_opa_gui(self, index):
        for gui in self.opa_guis:
            gui.hide()
        self.opa_guis[index].show()
        
    def update_mono_settings(self):
        self.mono_center.set_disabled(True)
        self.mono_width.set_disabled(True)
        self.mono_npts.set_disabled(True)
        method = self.mono_method_combo.read()
        if method == 'Set':
            self.mono_center.set_disabled(self.use_tune_points.read())
        elif method == 'Scan':
            self.mono_center.set_disabled(self.use_tune_points.read())
            self.mono_width.set_disabled(False)
            self.mono_npts.set_disabled(False)
        elif method == 'Static':
            self.mono_center.set_disabled(False)
        
def mkGUI():        
    global gui
    gui = GUI(module_name)
def load():
    return True

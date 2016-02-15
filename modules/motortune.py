### define ####################################################################


module_name = 'MOTORTUNE'


### import ####################################################################


import os
import sys
import time
import numexpr as ne

import numpy as np

import matplotlib
matplotlib.pyplot.ioff()

from PyQt4 import QtCore, QtGui
import WrightTools as wt

import project.project_globals as g
import project.classes as pc
import project.widgets as pw
import modules.scan as scan
app = g.app.read()


### import hardware control ###################################################


import spectrometers.spectrometers as spectrometers
import delays.delays as delays
import opas.opas as opas
import daq.daq as daq


### objects ###################################################################


class motor_gui():
    
    def __init__(self, name, center, width, number, use_tune_points):
        self.name = name
        self.use_tune_points = use_tune_points
        self.input_table = pw.InputTable()
        self.input_table.add(name, None)
        allowed = ['Set', 'Scan', 'Static']
        self.method = pc.Combo(allowed_values=allowed, disable_under_module_control=True)
        self.use_tune_points.updated.connect(self.update_disabled)
        self.method.updated.connect(self.update_disabled)
        self.input_table.add('Method', self.method)
        self.center = pc.Number(initial_value=center, disable_under_module_control=True)
        self.input_table.add('Center', self.center)
        self.width = pc.Number(initial_value=width, disable_under_module_control=True)
        self.input_table.add('Width', self.width)
        self.npts = pc.Number(initial_value=number, decimals=0, disable_under_module_control=True)
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


class OPA_gui():
    
    def __init__(self, hardware, layout, use_tune_points):
        self.hardware = hardware
        motor_names = self.hardware.address.ctrl.motor_names
        self.motors = []
        for name in motor_names:
            motor = motor_gui(name, 30, 1, 11, use_tune_points)
            layout.addWidget(motor.input_table)
            self.motors.append(motor)
        self.hide()  # initialize hidden
            
    def hide(self):
        for motor in self.motors:
            motor.input_table.hide()
    
    def show(self):
        for motor in self.motors:
            motor.input_table.show()


### gui #######################################################################


class GUI(scan.GUI):

    def create_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)
        # shared settings
        allowed = [hardware.name for hardware in opas.hardwares]
        self.opa_combo = pc.Combo(allowed, disable_under_module_control=True)
        self.opa_combo.updated.connect(self.update_opa_display)
        self.use_tune_points = pc.Bool(initial_value=True, disable_under_module_control=True)
        self.use_tune_points.updated.connect(self.update_mono_settings)
        input_table = pw.InputTable()
        input_table.add('OPA', self.opa_combo)
        input_table.add('Use Tune Points', self.use_tune_points)
        layout.addWidget(input_table)
        # OPA settings
        self.opa_guis = [OPA_gui(hardware, layout, self.use_tune_points) for hardware in opas.hardwares]
        self.opa_guis[0].show()
        # line
        line = pw.line('H')
        layout.addWidget(line)
        # mono settings
        allowed = ['Set', 'Scan', 'Static']
        self.mono_method_combo = pc.Combo(allowed, disable_under_module_control=True)
        self.mono_method_combo.updated.connect(self.update_mono_settings)
        self.mono_center = pc.Number(initial_value=7000, units='wn', disable_under_module_control=True)
        self.mono_center.set_disabled_units(True)
        self.mono_width = pc.Number(initial_value=500, units='wn', disable_under_module_control=True)
        self.mono_width.set_disabled_units(True)
        self.mono_npts = pc.Number(initial_value=51, decimals=0, disable_under_module_control=True)
        input_table = pw.InputTable()
        input_table.add('Spectrometer', None)
        input_table.add('Method', self.mono_method_combo)
        input_table.add('Center', self.mono_center)
        input_table.add('Width', self.mono_width)
        input_table.add('Number', self.mono_npts)
        layout.addWidget(input_table)
        self.update_mono_settings()
        # line
        line = pw.line('H')
        layout.addWidget(line)
        # processing
        input_table = pw.InputTable()
        input_table.add('Processing', None)
        self.do_post_process = pc.Bool(initial_value=True)
        input_table.add('Process', self.do_post_process)
        layout.addWidget(input_table)
        # scan widget
        layout.addWidget(self.scan.widget)
        # finish
        layout.addStretch(1)
        self.frame = QtGui.QWidget()
        self.frame.setLayout(layout)
        g.module_widget.add_child(self.frame)
        g.module_combobox.add_module(module_name, self.show_frame)

    def launch_scan(self):
        axes = []
        # get OPA properties
        opa_gui = self.opa_guis[self.opa_combo.read_index()]
        opa_hardware = opa_gui.hardware
        opa_friendly_name = opas.hardwares[self.opa_combo.read_index()].friendly_name
        curve = opa_hardware.address.ctrl.curve
        # tune points        
        if self.use_tune_points.read():
            motors_excepted = []  # list of indicies  
            for motor_index, motor in enumerate(opa_gui.motors):
                if not motor.method.read() == 'Set':
                    motors_excepted.append(motor_index)
            if self.mono_method_combo.read() == 'Set':
                identity = opa_friendly_name + '=wm'
                hardware_dict = {opa_friendly_name: [opa_hardware, 'set_position_except', ['destination', motors_excepted]],
                                 'wm': [spectrometers.hardwares[0], 'set_position', None]}
                axis = scan.Axis(curve.colors, curve.units, opa_friendly_name, identity, hardware_dict)
                axes.append(axis)
            else:
                hardware_dict = {opa_friendly_name: [opa_hardware, 'set_position_except', ['destination', motors_excepted]]}
                axis = scan.Axis(curve.colors, curve.units, opa_friendly_name, opa_friendly_name, hardware_dict)
                axes.append(axis)
        # motor
        for motor_index, motor in enumerate(opa_gui.motors):
            if motor.method.read() == 'Scan':
                motor_units = None
                name = '_'.join([opa_friendly_name, motor.name])
                width = motor.width.read()/2.
                npts = motor.npts.read()
                if self.use_tune_points.read():
                    center = 0.
                    identity = 'D'+name#+'F'+opa_friendly_name
                    curve_motor_index = curve.get_motor_names(full=False).index(motor.name)
                    motor_positions = curve.motors[curve_motor_index].positions
                    kwargs = {'centers': motor_positions, 
                              'centers_units': motor_units,
                              'centers_follow': opa_friendly_name}
                else:
                    center = motor.center.read()
                    identity = name
                    kwargs = {}
                points = np.linspace(center-width, center+width, npts)
                hardware_dict = {name: [opa_hardware, 'set_motor', [motor.name, 'destination']]}
                axis = scan.Axis(points, motor_units, name, identity, hardware_dict, **kwargs)
                axes.append(axis)
            elif motor.method.read() == 'Set':
                if self.use_tune_points.read():
                    pass
                else:
                    opa_hardware.q.push('set_motor', [motor.name, motor.center.read()])
            elif motor.method.read() == 'Static':
                opa_hardware.q.push('set_motor', [motor.name, motor.center.read()])
        # mono
        if self.mono_method_combo.read() == 'Scan':
            name = 'wm'
            units = 'wn'
            width = self.mono_width.read()/2.
            npts = self.mono_npts.read() 
            if self.use_tune_points.read():
                center = 0.
                identity = 'D'+name
                curve = curve.copy()
                curve.convert('wn')
                kwargs = {'centers': curve.colors,
                          'centers_units': curve.units,
                          'centers_follow': opa_friendly_name}
            else:
                center = self.mono_center.read()
                identity = name
                kwargs = {}
            points = np.linspace(center-width, center+width, npts)
            axis = scan.Axis(points, units, name, identity, **kwargs)
            axes.append(axis)
        elif self.mono_method_combo.read() == 'Set':
            if self.use_tune_points.read():
                # already handled above
                pass
            else:
                spectrometers.hardwares[0].set_position(self.mono_center.read(), self.mono_center.units)
        elif self.mono_method_combo.read() == 'Static':
            spectrometers.hardwares[0].set_position(self.mono_center.read(), self.mono_center.units)
        # launch
        pre_wait_methods = [lambda: opa_hardware.q.push('wait_until_still'),
                            lambda: opa_hardware.q.push('get_motor_positions'),
                            lambda: opa_hardware.q.push('get_position')]
        self.scan.launch(axes, constants=[], pre_wait_methods=pre_wait_methods)
        
    def on_done(self):
        '''
        Make pickle and figures.
        '''
        if not self.do_post_process.read():
            return
        # get path
        data_path = daq.data_path.read() 
        # make data object
        data = wt.data.from_PyCMDS(data_path, verbose=False)
        data.save(data_path.replace('.data', '.p'), verbose=False)
        # chop data if over 2D
        if len(data.shape) > 2:
            chopped_datas = data.chop(0, 1, verbose=False)
        # make figures for each channel
        data_folder, file_name, file_extension = wt.kit.filename_parse(data_path)
        # chop data if over 2D
        for channel_index, channel_name in enumerate(data.channel_names):
            image_fname = channel_name + ' ' + file_name
            if len(data.shape) == 1:
                artist = wt.artists.mpl_1D(data, verbose=False)
                artist.plot(channel_index, autosave=True, output_folder=data_folder,
                            fname=image_fname, verbose=False)
            elif len(data.shape) == 2:
                artist = wt.artists.mpl_2D(data, verbose=False)
                artist.plot(channel_index, autosave=True, output_folder=data_folder,
                            fname=image_fname, verbose=False)
            else:
                channel_folder = os.path.join(data_folder, channel_name)
                os.mkdir(channel_folder)
                for index, chopped_data in enumerate(chopped_datas):
                    this_image_fname = image_fname + str(index).zfill(3)
                    artist = wt.artists.mpl_2D(chopped_data, verbose=False)
                    artist.plot(channel_index, autosave=True, output_folder=channel_folder,
                                fname=this_image_fname, verbose=False)
                    g.app.read().processEvents()  # gui should not hang...
            # hack in a way to get the first image written
            if channel_index == 0:
                output_image_path = os.path.join(data_folder, image_fname + ' 000.png')
        # send message on slack
        if g.slack_enabled.read():
            slack = g.slack_control.read()
            slack.send_message('scan complete - {} elapsed'.format(g.progress_bar.time_elapsed.text()))
            if len(data.shape) < 3:
                print output_image_path
                slack.upload_file(output_image_path)
        
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

    def update_opa_display(self):
        for gui in self.opa_guis:
            gui.hide()
        self.opa_guis[self.opa_combo.read_index()].show()

gui = GUI(module_name)

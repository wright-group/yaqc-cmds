### import ####################################################################


from __future__ import absolute_import, division, print_function, unicode_literals

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
import somatic.acquisition as acquisition
import project.ini_handler as ini_handler
main_dir = g.main_dir.read()
ini = ini_handler.Ini(os.path.join(main_dir, 'somatic', 'modules', 'tune_test.ini'))
app = g.app.read()

import hardware.opas.opas as opas
import hardware.spectrometers.spectrometers as spectrometers
import devices.devices as devices

 
### define ####################################################################


module_name = 'POYNTING TUNE'
 
 
### Worker ####################################################################


class Worker(acquisition.Worker):
    
    def process(self, scan_folder):
        if self.do_2D:
            data_path = wt.kit.glob_handler('.data', folder=scan_folder)[0]
            data = wt.data.from_PyCMDS(data_path)
            channel_name = self.aqn.read('processing', 'channel')
            wt.tuning.workup.tune_test(data, curve, channel_name, save_directory=scan_folder)
            # upload
            self.upload(scan_folder, reference_image=os.path.join(scan_folder, 'tune test.png'))
    
    def run(self):
        axes = []
        possible_axes = {}
        # OPA
        opa_name = self.aqn.read('opa', 'opa')
        opa_names = [opa.name for opa in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        opa_hardware = opas.hardwares[opa_index]

        curve = opa_hardware.curve.copy()
        curve.convert('wn')

        axis = acquisition.Axis(curve.colors, 'wn', opa_name, opa_name)
        possible_axes[opa_name] = axis

        self.do_2D = self.aqn.read('processing', 'do_2D_scans')
        # mono
        for spec in spectrometers.hardwares:
            spec.set_position(0)

        for section in self.aqn.sections:
            if section not in ['opa','processing','device settings', 'Virtual', 'info']:
                if self.aqn.read(section, 'do'):
                    width = self.aqn.read(section,'width')
                    npts = int(self.aqn.read(section,'number'))
                    points = np.linspace(-width/2.,width/2., npts)
                    motor_positions = curve.motors[curve.motor_names.index(section)].positions
                    kwargs = {'center': motor_positions}
                    hardware_dict = {opa_name: [opa_hardware, 'set_motor', [section, 'destination']]}
                    axis = acquisition.Axis(points, None, opa_name, opa_name, hardware_dict, **kwargs)
                    possible_axes[section] = axis
                    
                

        if self.do_2D:
            self.axis_names = []
            axes.append(possible_axes[opa_name])
            for name, axis in possible_axes.items():
                if name is not opa_name:
                    axes.append(axis)
                    self.axis_names.append(name)
            # do scan
            self.scan(axes)
        else:
            for name, axis in possible_axes.items():
                if name is not opa_name:
                    axes.append(possible_axes[opa_name])
                    axes.append(axis)

                    scan_folder = self.scan(axes)

                    #process
                    p = os.path.join(scan_folder, '000.data')
                    data = wt.data.from_PyCMDS(p)
                    channel = self.aqn.read('processing', 'channel')
                    wt.tuning.workup.intensity(data, curve, channel, save_directory = scan_folder)

                    p = wt.kit.glob_handler('.curve', folder = scan_folder)[0]
                    opa_hardware.curve_path.write(p)

                    # upload
                    p = wt.kit.glob_handler('.png', folder = scan_folder)[0]
                    self.upload(scan_folder, reference_image = p)

        # finish
        if not self.stopped.read():
            self.finished.write(True)  # only if acquisition successfull

 
### GUI #######################################################################


class GUI(acquisition.GUI):

    def create_frame(self):
        input_table = pw.InputTable()
        # opa combo
        allowed = [hardware.name for hardware in opas.hardwares if hardware.driver.poynting_correction is not None]
        self.opa_combo = pc.Combo(allowed)
        self.opa_combo.updated.connect(self.on_opa_combo_updated)
        input_table.add('OPA', self.opa_combo)

        self.do_2D_scans = pc.Bool()
        input_table.add("Do 2D scans", self.do_2D_scans)
        self.do_2D_scans.updated.connect(self.on_do_2D_scans_updated)

        self.layout.addWidget(input_table)

        # motor selection
        self.opa_guis = [OPA_GUI(hardware, self.layout) for hardware in opas.hardwares]
        self.opa_guis[0].show()



        input_table = pw.InputTable()

        # processing
        input_table.add('Processing', None)
        self.channel_combo = pc.Combo(allowed_values=devices.control.channel_names, ini=ini, section='main', option='channel name')
        input_table.add('Channel', self.channel_combo)
        # finish
        self.layout.addWidget(input_table)
        
    def load(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        self.opa_combo.write(aqn.read('opa', 'opa'))
        self.do_2D_scans.write(aqn.read('processing', 'do_2D_scans'))
        opa_gui = self.opa_guis[self.opa_combo.read_index()]
        for motor in opa_gui.motors:
            motor.do.write(aqn.read(motor.name, 'do'))
            motor.width.write(aqn.read(motor.name, 'width'))
            motor.number.write(aqn.read(motor.name, 'number'))

        self.channel_combo.write(aqn.read('processing', 'channel'))
        # allow devices to load settings
        self.device_widget.load(aqn_path)
        
    def on_opa_combo_updated(self):
        self.show_opa_gui(self.opa_combo.read_index())

    def show_opa_gui(self, index):
        for gui in self.opa_guis:
            gui.hide()
        self.opa_guis[index].show()

    def on_do_2D_scans_updated(self):
        do_2D = self.do_2D_scans.read()
        opa_gui = self.opa_guis[self.opa_combo.read_index()]

        if do_2D:
            for motor in opa_gui.motors:
                motor.do.set_disabled(True)
                motor.do.write(True)
        else:
            for motor in opa_gui.motors:
                motor.do.set_disabled(False)

    def on_device_settings_updated(self):
        self.channel_combo.set_allowed_values(devices.control.channel_names)
        
    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        aqn.write('info', 'description', '{} tune test'.format(self.opa_combo.read()))
        aqn.add_section('opa')
        aqn.write('opa', 'opa', self.opa_combo.read())

        opa_gui = self.opa_guis[self.opa_combo.read_index()]
        for motor in opa_gui.motors:
            aqn.add_section(motor.name)
            aqn.write(motor.name, 'do', motor.do.read())
            aqn.write(motor.name, 'width', motor.width.read())
            aqn.write(motor.name, 'number', motor.number.read())
        aqn.add_section('processing')
        aqn.write('processing', 'do_2D_scans', self.do_2D_scans.read())
        aqn.write('processing', 'channel', self.channel_combo.read())
        # allow devices to write settings
        print(self.device_widget)
        self.device_widget.save(aqn_path)

class OPA_GUI():
    def __init__(self,hardware,layout):
        self.hardware = hardware
        motor_names = self.hardware.curve.motor_names
        self.motors = []
        for name in motor_names:
            motor = MotorGUI(name,1000,31)
            if layout is not None:
                layout.addWidget(motor.input_table)
            self.motors.append(motor)
        self.hide()

    def hide(self):
        for motor in self.motors:
            motor.input_table.hide()
    def show(self):
        for motor in self.motors:
            motor.input_table.show()

class MotorGUI():
    def __init__(self, name, width, number):
        self.name = name
        self.input_table = pw.InputTable()

        self.input_table.add(name, None)
        self.do = pc.Bool()
        self.input_table.add('Do', self.do)

        self.width = pc.Number(initial_value = width, decimals = 0)
        self.input_table.add('Width', self.width)

        self.number = pc.Number(initial_value = number, decimals = 0)
        self.input_table.add('Number', self.number)
        
        
gui = GUI(module_name)

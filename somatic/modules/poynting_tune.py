### import ####################################################################


import configparser
import os
import sys
import time
import numexpr as ne

import numpy as np

import matplotlib
matplotlib.pyplot.ioff()

from PySide2 import QtCore, QtWidgets
import WrightTools as wt
import attune

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


module_name = 'AUTOTUNE'
 
 
### Worker ####################################################################


class Worker(acquisition.Worker):

    def process(self, scan_folder):
        pass
    
    def run(self):
        axes = []
        possible_axes = {}
        # OPA
        opa_name = self.aqn.read('opa', 'opa')
        opa_names = [opa.name for opa in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        opa_hardware = opas.hardwares[opa_index]

        # mono
        for spec in spectrometers.hardwares:
            spec.set_position(0)
            

        for section in self.aqn.sections:
            try:
                if self.aqn.read(section, 'do'):
                    curve = opa_hardware.curve.copy()
                    while not section in curve.dependent_names:
                        curve = curve.subcurve
                    curve.convert("wn")
                    width = self.aqn.read(section,'width')
                    npts = int(self.aqn.read(section,'number'))
                    points = np.linspace(-width/2.,width/2., npts)
                    motor_positions = curve[section][:]
                    kwargs = {'centers': motor_positions}
                    hardware_dict = {opa_name: [opa_hardware, 'set_motor', [section, 'destination']]}
                    axis = acquisition.Axis(points, None, opa_name+'_'+section, 'D'+opa_name, hardware_dict, **kwargs)
                    possible_axes[section] = axis
            except configparser.NoOptionError:
                pass
                

        for name, axis in possible_axes.items():
            curve = opa_hardware.curve.copy()
            curve_ids = list(opa_hardware.driver.curve_paths.keys())
            while not name in curve.dependent_names:
                curve = curve.subcurve
                curve_ids = curve_ids[:-1]
            curve_id = curve_ids[-1]
            curve.convert('wn')                    
            
            axes = []
            # Note: if the top level curve covers different ranges than the subcurves,
            # This will behave quite poorly...
            # It will need to be changed to accomodate more complex hierarchies, e.g. TOPAS
            # It should handle top level curves, even for topas, though
            # 2019-08-28 KFS
            opa_axis = acquisition.Axis(curve.setpoints[:], 'wn', opa_name, opa_name)
            axes.append(opa_axis)
            axes.append(axis)
            
            scan_folder = self.scan(axes)

            #process
            p = os.path.join(scan_folder, '000.data')
            data = wt.data.from_PyCMDS(p)
            channel = self.aqn.read(name, 'channel')
            transform = list(data.axis_names)
            dep = name
            transform[-1] = f"{transform[0]}_{dep}_points"
            data.transform(*transform)
            attune.workup.intensity(data, channel, dep, curve, save_directory = scan_folder, gtol=1e-3)

            if not self.stopped.read():
                p = wt.kit.glob_handler('.curve', folder = scan_folder)[0]
                opa_hardware.driver.curve_paths[curve_id].write(p)

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
        allowed = [hardware.name for hardware in opas.hardwares]
        if not allowed:
            return
        self.opa_combo = pc.Combo(allowed)
        self.opa_combo.updated.connect(self.on_opa_combo_updated)
        input_table.add('OPA', self.opa_combo)

        self.layout.addWidget(input_table)

        # motor selection
        self.opa_guis = [OPA_GUI(hardware, self.layout) for hardware in opas.hardwares]
        self.opa_guis[0].show()

        input_table = pw.InputTable()

        # finish
        self.layout.addWidget(input_table)
        
    def load(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        self.opa_combo.write(aqn.read('opa', 'opa'))
        opa_gui = self.opa_guis[self.opa_combo.read_index()]
        for motor in opa_gui.motors:
            motor.do.write(aqn.read(motor.name, 'do'))
            motor.width.write(aqn.read(motor.name, 'width'))
            motor.number.write(aqn.read(motor.name, 'number'))
            motor.channel_combo.write(aqn.read(motor.name, 'channel'))
        # allow devices to load settings
        self.device_widget.load(aqn_path)
        
    def on_opa_combo_updated(self):
        self.show_opa_gui(self.opa_combo.read_index())

    def show_opa_gui(self, index):
        for gui in self.opa_guis:
            gui.hide()
        self.opa_guis[index].show()

    def on_device_settings_updated(self):
        for gui in self.opa_guis:
            for motor in gui.motors:
                motor.channel_combo.set_allowed_values(devices.control.channel_names)
        
    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        aqn.write('info', 'description', '{} Auto Tune'.format(self.opa_combo.read()))
        aqn.add_section('opa')
        aqn.write('opa', 'opa', self.opa_combo.read())

        opa_gui = self.opa_guis[self.opa_combo.read_index()]
        for motor in opa_gui.motors:
            aqn.add_section(motor.name)
            aqn.write(motor.name, 'do', motor.do.read())
            aqn.write(motor.name, 'width', motor.width.read())
            aqn.write(motor.name, 'number', motor.number.read())
            aqn.write(motor.name, 'channel', motor.channel_combo.read())
        # allow devices to write settings
        self.device_widget.save(aqn_path)

class OPA_GUI():
    def __init__(self,hardware,layout):
        self.hardware = hardware
        curve = self.hardware.curve
        motor_names = curve.dependent_names
        self.motors = []
        for name in motor_names:
            # TODO: per motor defaults
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

        self.channel_combo = pc.Combo(allowed_values=devices.control.channel_names)
        self.input_table.add('Channel', self.channel_combo)
        
        
def load():
    return True

def mkGUI():        
    global gui
    gui = GUI(module_name)

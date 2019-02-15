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
import attune

import project.project_globals as g
import project.classes as pc
import project.widgets as pw
import somatic.acquisition as acquisition
from somatic.modules.scan import Axis as ScanAxisGUI
from somatic.modules.scan import Constant
import project.ini_handler as ini_handler
main_dir = g.main_dir.read()
ini = ini_handler.Ini(os.path.join(main_dir, 'somatic', 'modules', 'zero_tune.ini'))
app = g.app.read()

import hardware.spectrometers.spectrometers as spectrometers
import hardware.delays.delays as delays
import hardware.opas.opas as opas
import hardware.filters.filters as filters
all_hardwares = opas.hardwares + spectrometers.hardwares + delays.hardwares + filters.hardwares
import devices.devices as devices

 
### define ####################################################################


module_name = 'ZERO TUNE'
 
 
### Worker ####################################################################


class Worker(acquisition.Worker):
    
    def process(self, scan_folder):
        data_path = wt.kit.glob_handler('.data', folder=scan_folder)[0]
        data = wt.data.from_PyCMDS(data_path)
        opa_name = self.aqn.read('opa', 'opa')
        opa_names = [opa.name for opa in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        opa = opas.hardwares[opa_index]
        delays = self.aqn.read('delay', 'delays')
        channel_name = self.aqn.read('processing', 'channel')
        # This can be simplified, I guess, as it is known which will occur in what order
        color_units = [i.units for i in data.axes if wt.units.kind(i.units) == 'energy'][0]
        delay_units = [i.units for i in data.axes if wt.units.kind(i.units) == 'delay'][0]
        for delay in delays: 
            attune.workup.intensity(data, channel_name, delay, cutoff_factor=0, save_directory=scan_folder)
        # upload
        self.upload(scan_folder)
    
    def run(self):
        axes = []
        # OPA
        opa_name = self.aqn.read('opa', 'opa')
        opa_names = [opa.name for opa in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        opa_hardware = opas.hardwares[opa_index]
        opa_friendly_name = opa_hardware.name
        curve = opa_hardware.curve.copy()
        curve.convert('wn')
        axis = acquisition.Axis(curve.setpoints, 'wn', opa_friendly_name, opa_friendly_name)
        axes.append(axis)
        # delay
        axis_name = 'delay'
        start = self.aqn.read(axis_name, 'start')
        stop = self.aqn.read(axis_name, 'stop')
        number = self.aqn.read(axis_name, 'number')
        points = np.linspace(start, stop, number)
        units = self.aqn.read(axis_name, 'units')
        name = '='.join(self.aqn.read(axis_name, 'delays'))
        axis = acquisition.Axis(points, units, name, name)
        axes.append(axis)
        
        constants = []
        for constant_name in self.aqn.read('scan', 'constant names'):
            for hardware in all_hardwares:
                if hardware.name == constant_name:
                    units = hardware.units
                    if wt.units.kind(units) == 'energy':
                        units = 'wn'
                    break
            name = constant_name
            identity = expression = self.aqn.read(constant_name, 'expression')
            constant = acquisition.Constant(units, name, identity, expression=expression, static=False)
            constants.append(constant)
        # do scan
        self.scan(axes, constants)
        # finish
        if not self.stopped.read():
            self.finished.write(True)  # only if acquisition successfull

 
### GUI #######################################################################


class GUI(acquisition.GUI):

    def create_frame(self):
        input_table = pw.InputTable()
        # opa combo
        allowed = [hardware.name for hardware in opas.hardwares]
        self.opa_combo = pc.Combo(allowed)
        input_table.add('OPA', None)
        input_table.add('OPA', self.opa_combo)
        # delay
        self.delay = ScanAxisGUI('delay', "")
        self.delay.start.write(-3)
        self.delay.stop.write(3)
        self.delay.number.write(21)
        input_table.add('Delay', None)
        self.layout.addWidget(self.delay.widget)
        # constants
        self.constants = []
        input_table.add('Constants', None)
        self.layout.addWidget(input_table)
        self.constants_container_widget = QtGui.QWidget()
        self.constants_container_widget.setLayout(QtGui.QVBoxLayout())
        self.constants_container_widget.layout().setMargin(0)
        self.layout.addWidget(self.constants_container_widget)
        add_constant_button, remove_constant_button = self.add_buttons()
        add_constant_button.clicked.connect(self.add_constant)
        remove_constant_button.clicked.connect(self.remove_constant)
        # processing
        input_table.add('Processing', None)
        self.channel_combo = pc.Combo(allowed_values=devices.control.channel_names, ini=ini, section='main', option='channel name')
        input_table.add('Channel', self.channel_combo)
        # finish
        self.layout.addWidget(input_table)
    
    def add_constant(self):
        #if len(self.constants) == 1: return  # temporary...
        constant = Constant()
        self.constants_container_widget.layout().addWidget(constant.widget)
        self.constants.append(constant)

    def add_buttons(self):
        colors = g.colors_dict.read()
        # layout
        button_container = QtGui.QWidget()
        button_container.setLayout(QtGui.QHBoxLayout())
        button_container.layout().setMargin(0)
        # remove
        remove_button = QtGui.QPushButton()
        remove_button.setText('REMOVE')
        remove_button.setMinimumHeight(25)
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors['stop'])
        remove_button.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(remove_button)
        # add
        add_button = QtGui.QPushButton()
        add_button.setText('ADD')
        add_button.setMinimumHeight(25)
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors['set'])
        add_button.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(add_button)
        # finish
        self.layout.addWidget(button_container)
        return [add_button, remove_button]

    def load(self, aqn_path):
        for constant in self.constants:
            constant.hide()
        self.constants = []
        aqn = wt.kit.INI(aqn_path)
        self.opa_combo.write(aqn.read('opa', 'opa'))
        self.mono_width.write(aqn.read('spectrometer', 'width'))
        self.mono_npts.write(aqn.read('spectrometer', 'number'))
        self.channel_combo.write(aqn.read('processing', 'channel'))
        # constants
        constant_names = aqn.read('scan', 'constant names')
        for constant_index, constant_name in enumerate(constant_names):
            constant = Constant()
            constant.hardware_name_combo.write(aqn.read(constant_name, 'hardware'))
            constant.expression.write(aqn.read(constant_name, 'expression'))
            self.constants.append(constant)
            self.constants_container_widget.layout().addWidget(constant.widget)
        # allow devices to load settings
        self.device_widget.load(aqn_path)

    def remove_constant(self):
        # remove trailing constant
        if len(self.constants) > 0:
            constant = self.constants[-1]
            self.constants_container_widget.layout().removeWidget(constant.widget)
            constant.hide()
            self.constants.pop(-1)
        
    def on_device_settings_updated(self):
        self.channel_combo.set_allowed_values(devices.control.channel_names)
        
    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        aqn.add_section('opa')
        aqn.write('opa', 'opa', self.opa_combo.read())
        aqn.add_section('delay')
        aqn.write('delay', 'start', self.delay.start.read())
        aqn.write('delay', 'stop', self.delay.stop.read())
        aqn.write('delay', 'number', self.delay.number.read())
        aqn.write('delay', 'units', self.delay.units)
        hardwares = []
        for key, bool_mutex in self.delay.hardwares.items():
            if bool_mutex.read():
                hardwares.append(key)
        aqn.write('delay', 'delays', hardwares)
        aqn.write('info', 'description', '{} {} zero tune'.format(self.opa_combo.read(), hardwares))
        # constants
        aqn.add_section('scan')
        aqn.write("scan", "constant names", [c.get_name() for c in self.constants])
        for constant in self.constants:
            name = constant.get_name()
            aqn.add_section(name)
            aqn.write(name, 'hardware', constant.hardware_name_combo.read())
            aqn.write(name, 'expression', constant.expression.read())
        aqn.add_section('processing')
        aqn.write('processing', 'channel', self.channel_combo.read())
        # allow devices to write settings
        print(self.device_widget)
        self.device_widget.save(aqn_path)
        
def load():
    return True
def mkGUI():        
    global gui
    gui = GUI(module_name)

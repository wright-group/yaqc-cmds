### define ####################################################################


module_name = 'SCAN'


### import ####################################################################


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
all_hardwares = opas.hardwares + spectrometers.hardwares + delays.hardwares


### classes ###################################################################


class Axis():
    
    def __init__(self, units_kind, axis_index):
        self.units_kind = units_kind
        if self.units_kind == 'energy':
            self.units = 'wn'
            initial_start = 1500
            initial_stop = 1200
        elif self.units_kind == 'delay':
            self.units = 'ps'
            initial_start = -1
            initial_stop = 1
        self.widget = pw.InputTable()
        g.module_control.disable_when_true(self.widget)
        self.widget.add(str(axis_index) + ' (' + self.units_kind + ')', None)
        # start
        self.start = pc.Number(initial_value=initial_start, units=self.units)
        self.start.set_disabled_units(True)
        self.widget.add('Initial', self.start)
        # stop
        self.stop = pc.Number(initial_value=initial_stop, units=self.units)
        self.stop.set_disabled_units(True)
        self.widget.add('Final', self.stop)
        # number
        self.number = pc.Number(initial_value=51, decimals=0)
        self.widget.add('Number', self.number)
        # hardwares
        if self.units_kind == 'energy':
            hardware_objs = opas.hardwares + spectrometers.hardwares
        elif self.units_kind == 'delay':
            hardware_objs = delays.hardwares
        self.hardwares = {}
        for hw in hardware_objs:
            checkbox = pc.Bool()
            self.widget.add(hw.friendly_name, checkbox)
            self.hardwares[hw.friendly_name] = checkbox
            
    def hide(self):
        self.widget.hide()
        
        
class Constant():
    
    def __init__(self):
        self.widget = pw.InputTable()
        g.module_control.disable_when_true(self.widget)
        self.widget.add('Constant', None)
        # hardware name
        allowed_values = [h.friendly_name for h in all_hardwares]
        self.hardware_name_combo = pc.Combo(allowed_values=allowed_values)
        self.hardware_name_combo.write('wm')
        self.hardware_name_combo.set_disabled(True)
        self.widget.add('Hardware', self.hardware_name_combo)
        # expression
        self.expression = pc.String(initial_value='w1+w2+12500')
        self.widget.add('Expression', self.expression)
        
    def hide(self):
        self.widget.hide()

 
### gui #######################################################################


class GUI(scan.GUI):

    def create_frame(self):
        self.layout = QtGui.QVBoxLayout()
        self.layout.setMargin(5)
        # axes
        self.axes = []
        input_table = pw.InputTable()
        input_table.add('Axes', None)
        self.layout.addWidget(input_table)
        self.axes_container_widget = QtGui.QWidget()
        self.axes_container_widget.setLayout(QtGui.QVBoxLayout())
        self.axes_container_widget.layout().setMargin(0)
        self.layout.addWidget(self.axes_container_widget)
        add_energy_axis_button = pw.SetButton('ADD ENERGY AXIS')
        add_energy_axis_button.clicked.connect(lambda: self.add_axis('energy'))
        g.module_control.disable_when_true(add_energy_axis_button)
        self.layout.addWidget(add_energy_axis_button)
        add_delay_axis_button = pw.SetButton('ADD DELAY AXIS')
        add_delay_axis_button.clicked.connect(lambda: self.add_axis('delay'))
        g.module_control.disable_when_true(add_delay_axis_button)
        self.layout.addWidget(add_delay_axis_button)
        remove_axis_button = pw.SetButton('REMOVE AXIS', 'stop')
        remove_axis_button.clicked.connect(self.remove_axis)
        g.module_control.disable_when_true(remove_axis_button)
        self.layout.addWidget(remove_axis_button)
        # constants
        self.constants = []
        line = pw.line('H')
        self.layout.addWidget(line)
        input_table = pw.InputTable()
        input_table.add('Constants', None)
        self.layout.addWidget(input_table)
        self.constants_container_widget = QtGui.QWidget()
        self.constants_container_widget.setLayout(QtGui.QVBoxLayout())
        self.constants_container_widget.layout().setMargin(0)
        self.layout.addWidget(self.constants_container_widget)
        add_constant_button, remove_constant_button = self.add_buttons()
        add_constant_button.clicked.connect(self.add_constant)
        remove_constant_button.clicked.connect(self.remove_constant)
        # scan widget
        line = pw.line('H')
        self.layout.addWidget(line)
        self.layout.addWidget(self.scan.widget)
        # finish
        self.layout.addStretch(1)
        self.frame = QtGui.QWidget()
        self.frame.setLayout(self.layout)
        g.module_widget.add_child(self.frame)
        g.module_combobox.add_module(module_name, self.show_frame)
        
    def add_axis(self, units_kind):
        axis = Axis(units_kind, len(self.axes))
        self.axes_container_widget.layout().addWidget(axis.widget)
        self.axes.append(axis)
        
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
        g.module_control.disable_when_true(remove_button)
        # add
        add_button = QtGui.QPushButton()
        add_button.setText('ADD')
        add_button.setMinimumHeight(25)
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors['set'])
        add_button.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(add_button)
        g.module_control.disable_when_true(add_button)
        # finish
        self.layout.addWidget(button_container)
        return [add_button, remove_button]
        
    def add_constant(self):
        if len(self.constants) == 1: return  # temporary...
        constant = Constant()
        self.constants_container_widget.layout().addWidget(constant.widget)
        self.constants.append(constant)
            
    def remove_axis(self):
        # remove trailing axis
        if len(self.axes) > 0:
            axis = self.axes[-1]
            self.axes_container_widget.layout().removeWidget(axis.widget)
            axis.hide()
            self.axes.pop(-1)
        
    def remove_constant(self):
        # remove trailing constant
        if len(self.constants) > 0:
            constant = self.constants[-1]
            self.constants_container_widget.layout().removeWidget(constant.widget)
            constant.hide()
            self.constants.pop(-1)
            
    def launch_scan(self):
        # check if settings are valid
        if len(self.axes) == 0:
            print 'YOU MUST HAVE AT LEAST ONE AXIS TO DO A SCAN!!!'
            self.scan.done.emit()
            return
        for axis in self.axes:
            bools = [b.read() for b in axis.hardwares.values()]
            if not any(bools):
                print 'EACH AXIS MUST HAVE AT LEAST ONE HARDWARE!!!'
                self.scan.done.emit()
        # construct axes
        scan_axes = []
        for axis in self.axes:
            # points
            start = axis.start.read()
            stop = axis.stop.read()
            number = axis.number.read()
            points = np.linspace(start, stop, number)
            # units
            units = axis.units
            # name, identity
            hw_names = [n for n, b in axis.hardwares.items() if b.read()]
            name = ''.join(hw_names)
            identity = '='.join(hw_names)
            # finish
            scan_axis = scan.Axis(points, units, name, identity)
            scan_axes.append(scan_axis)
        # construct constants
        scan_constants = []
        for constant in self.constants:
            name = constant.hardware_name_combo.read()
            identity = constant.expression.read()
            expression = constant.expression.read()
            scan_constant = scan.Constant('wn', name, identity, static=False, expression=expression)
            scan_constants.append(scan_constant)
        # finish
        self.scan.launch(scan_axes, scan_constants)

gui = GUI(module_name)

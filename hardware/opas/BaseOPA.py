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

import project.classes as pc
import project.widgets as pw
import project.project_globals as g
from project.ini_handler import Ini
main_dir = g.main_dir.read()
                                 
### OPA object ################################################################


class BaseOPA:

    def __init__(self, native_units):
        self.native_units = native_units
        # mutex attributes
        self.limits = pc.NumberLimits(units=self.native_units)
        self.current_position = pc.Number(name='Color', initial_value=1300.,
                                          limits=self.limits,
                                          units=self.native_units, display=True,
                                          set_method='set_position')
        self.offset = pc.Number(initial_value=0, units=self.native_units, display=True)
        # objects to be sent to PyCMDS
        self.exposed = [self.current_position]
        self.recorded = collections.OrderedDict()
        ##
        self.motor_names = []
        # finish
        self.gui = BaseOPAGUI(self)
        self.initialized = pc.Bool()
        self.homeable = [False]
        
    ## TODO: implement _set_motors in pico opa
    def _set_motors(self, motor_indexes, motor_destinations, wait=True):
        raise NotImplementedError

    def _home_motors(self, motor_indexes):
        raise NotImplementedError

    def home_motor(self, inputs):
        motor_name = inputs[0]
        motor_index = self.motor_names.index(motor_name)
        if self.homeable[motor_index % len(self.homeable)]:
            self._home_motors([motor_index])

    def home_all(self, inputs=[]):
        indexes = range(len(self.motor_names))
        indexes = [i for i in indexes if self.homeable[i%len(self.homeable)] ]
        self._home_motors(indexes)
                    
    def close(self):
        raise NotImplementedError
        
    def _update_api(self, interaction):
        pass

    def _load_curve(self, inputs, interaction):
        raise NotImplementedError

    def load_curve(self, inputs=[]):
        '''
        inputs can be none (so it loads current curves) 
        or ['curve type', filepath]
        '''
        # update own curve object
        interaction = self.interaction_string_combo.read()
        self._load_curve(inputs, interaction)
        # update limits
        min_color = self.curve.colors.min()
        max_color = self.curve.colors.max()
        self.limits.write(min_color, max_color, self.native_units)
        self._update_api(interaction)
        
    def get_crv_paths(self):
        return [o.read() for o in self.curve_paths.values()]

    def get_points(self):
        return self.curve.colors

    def get_position(self):
        position = self.address.hardware.destination.read(self.native_units)
        self.current_position.write(position)
        return position
        
    # TODO Figure out what this should do/what calls this
    def get_motor_positions(self, inputs=[]):
        raise NotImplementedError
    
    def initialize(self, inputs, address):
        '''
        OPA initialization method. Inputs = [index]
        '''
        raise NotImplementedError

    def is_busy(self):
        raise NotImplementedError

    def set_offset(self, offset):
        pass

    def set_position(self, destination):
        # coerce destination to be within current tune range
        destination = np.clip(destination, self.curve.colors.min(), self.curve.colors.max())
        # get destinations from curve
        motor_names = self.curve.get_motor_names()
        motor_destinations = self.curve.get_motor_positions(destination, self.native_units)
        # send command
        motor_indexes = [self.motor_names.index(n) for n in motor_names]
        self._set_motors(motor_indexes, motor_destinations)
        # finish
        self.get_position()
        
    def set_position_except(self, inputs):
        '''
        set position, except for motors that follow
        
        does not wait until still...
        '''
        destination = inputs[0]
        self.address.hardware.destination.write(destination)
        self.current_position.write(destination, 'nm')
        exceptions = inputs[1]  # list of integers
        motor_destinations = self.curve.get_motor_positions(destination, 'nm')
        motor_indexes = []
        motor_positions = []
        for i in [self.motor_names.index(n) for n in self.curve.get_motor_names()]:
            if i not in exceptions:
                motor_indexes.append(i)
                motor_positions.append(motor_destinations[i])
        self._set_motors(motor_indexes, motor_positions, wait=False)
        
    def set_motor(self, inputs):
        '''
        inputs [motor_name (str), destination (steps)]
        '''
        motor_name, destination = inputs
        motor_index = self.motor_names.index(motor_name)
        self._set_motors([motor_index], [destination])

    def set_motors(self, inputs):
        motor_indexes = range(len(inputs))
        motor_positions = inputs
        self._set_motors(motor_indexes, motor_positions)

    def wait_until_still(self, inputs=[]):
        while self.is_busy():
            time.sleep(0.1)  # I've experienced hard crashes when wait set to 0.01 - Blaise 2015.12.30
            self.get_motor_positions()
        self.get_motor_positions()
    
### gui #######################################################################
    
## TODO: Should MotorControlGUI be in the abstracted class
class MotorControlGUI(QtGui.QWidget):
    
    def __init__(self, motor_name, motor_mutex, driver):
        QtGui.QWidget.__init__(self)
        self.motor_name = motor_name
        self.driver = driver
        self.layout = QtGui.QVBoxLayout()
        self.layout.setMargin(0)
        # table
        input_table = pw.InputTable()
        input_table.add(motor_name, motor_mutex)
        self.destination = motor_mutex.associate(display=False)
        input_table.add('Dest. ' + motor_name, self.destination)
        self.layout.addWidget(input_table)
        # buttons
        home_button, set_button = self.add_buttons(self.layout, 'HOME', 'advanced', 'SET', 'set')
        home_button.clicked.connect(self.on_home)
        set_button.clicked.connect(self.on_set)
        g.queue_control.disable_when_true(home_button)
        g.queue_control.disable_when_true(set_button)
        # finish
        self.setLayout(self.layout)
            
    def add_buttons(self, layout, button1_text, button1_color, button2_text, button2_color):
        colors = g.colors_dict.read()
        # layout
        button_container = QtGui.QWidget()
        button_container.setLayout(QtGui.QHBoxLayout())
        button_container.layout().setMargin(0)
        # button1
        button1 = QtGui.QPushButton()
        button1.setText(button1_text)
        button1.setMinimumHeight(25)
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors[button1_color])
        button1.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(button1)
        g.queue_control.disable_when_true(button1)
        # button2
        button2 = QtGui.QPushButton()
        button2.setText(button2_text)
        button2.setMinimumHeight(25)
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors[button2_color])
        button2.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(button2)
        g.queue_control.disable_when_true(button2)
        # finish
        layout.addWidget(button_container)
        return [button1, button2]
        
    def on_home(self):
        self.driver.address.hardware.q.push('home_motor', [self.motor_name])
    
    def on_set(self):
        destination = self.destination.read()
        self.driver.address.hardware.q.push('set_motor', [self.motor_name, destination])


class BaseOPAGUI(QtCore.QObject):

    def __init__(self, driver):
        QtCore.QObject.__init__(self)
        self.driver = driver
        self.layout = None

    def create_frame(self, layout):
        layout.setMargin(5)
        self.layout = layout
        self.frame = QtGui.QWidget()
        self.frame.setLayout(self.layout)
        if self.driver.initialized.read():
            self.initialize()
        else:
            self.driver.initialized.updated.connect(self.initialize)

    def initialize(self):
        # container widget
        display_container_widget = QtGui.QWidget()
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        self.layout.addWidget(display_container_widget)
        # plot
        self.plot_widget = pw.Plot1D()
        self.plot_widget.plot_object.setMouseEnabled(False, False)
        self.plot_curve = self.plot_widget.add_scatter()
        self.plot_h_line = self.plot_widget.add_infinite_line(angle=0, hide=False)
        self.plot_v_line = self.plot_widget.add_infinite_line(angle=90, hide=False)
        display_layout.addWidget(self.plot_widget)
        # vertical line
        line = pw.line('V')
        self.layout.addWidget(line)
        # container widget / scroll area
        settings_container_widget = QtGui.QWidget()
        settings_scroll_area = pw.scroll_area()
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        self.layout.addWidget(settings_scroll_area)
        # opa properties
        input_table = pw.InputTable()
        if self.driver.serial_number != -1:
            serial_number_display = pc.Number(initial_value=self.driver.serial_number, decimals=0, display=True)
            input_table.add('Serial Number', serial_number_display)
        settings_layout.addWidget(input_table)
        # plot control
        input_table = pw.InputTable()
        input_table.add('Display', None)
        self.plot_motor = pc.Combo(allowed_values=self.driver.curve.get_motor_names())
        self.plot_motor.updated.connect(self.update_plot)
        input_table.add('Motor', self.plot_motor)
        allowed_values = wt.units.energy.keys()
        allowed_values.remove('kind')
        self.plot_units = pc.Combo(initial_value=self.driver.native_units, allowed_values=allowed_values)
        self.plot_units.updated.connect(self.update_plot)
        input_table.add('Units', self.plot_units)
        settings_layout.addWidget(input_table)
        # curves
        input_table = pw.InputTable()
        input_table.add('Curves', None)
        for name, obj in self.driver.curve_paths.items():
            input_table.add(name, obj)
            obj.updated.connect(self.update_plot)
        input_table.add('Interaction String', self.driver.interaction_string_combo)
        self.low_energy_limit_display = pc.Number(units=self.driver.native_units, display=True)
        input_table.add('Low Energy Limit', self.low_energy_limit_display)
        self.high_energy_limit_display = pc.Number(units=self.driver.native_units, display=True)
        input_table.add('High Energy LImit', self.high_energy_limit_display)
        settings_layout.addWidget(input_table)
        self.driver.limits.updated.connect(self.on_limits_updated)
        # motors
        input_table = pw.InputTable()
        input_table.add('Motors', None)
        settings_layout.addWidget(input_table)
        for motor_name, motor_mutex in self.driver.motor_positions.items():
            settings_layout.addWidget(MotorControlGUI(motor_name, motor_mutex, self.driver))
        self.home_all_button = pw.SetButton('HOME ALL', 'advanced')
        settings_layout.addWidget(self.home_all_button)
        self.home_all_button.clicked.connect(self.on_home_all)
        g.queue_control.disable_when_true(self.home_all_button)
        # stretch
        settings_layout.addStretch(1)
        # signals and slots
        self.driver.interaction_string_combo.updated.connect(self.update_plot)
        self.driver.address.update_ui.connect(self.update)
        # finish
        self.update()
        self.update_plot()
        self.on_limits_updated()
        # autotune
        self.driver.auto_tune.initialize()

    def update(self):
        print 'OPA update'
        # set button disable
        if self.driver.address.busy.read():
            self.home_all_button.setDisabled(True)
            for motor_mutex in self.driver.motor_positions.values():
                motor_mutex.set_disabled(True)
        else:
            self.home_all_button.setDisabled(False)
            for motor_mutex in self.driver.motor_positions.values():
                motor_mutex.set_disabled(False)
        # update destination motor positions
        # TODO: 
        # update plot lines
        motor_name = self.plot_motor.read()
        motor_position = self.driver.motor_positions[motor_name].read()
        self.plot_h_line.setValue(motor_position)
        units = self.plot_units.read()
        self.plot_v_line.setValue(self.driver.current_position.read(units))

    def update_plot(self):
        # units
        units = self.plot_units.read()
        # xi
        colors = self.driver.curve.colors
        xi = wt_units.converter(colors, self.driver.native_units, units)
        # yi
        self.plot_motor.set_allowed_values(self.driver.curve.get_motor_names())
        motor_name = self.plot_motor.read()
        motor_index = self.driver.curve.get_motor_names().index(motor_name)
        yi = self.driver.curve.get_motor_positions(colors, units)[motor_index]
        self.plot_widget.set_labels(xlabel=units, ylabel=motor_name)
        self.plot_curve.clear()
        self.plot_curve.setData(xi, yi)
        self.plot_widget.graphics_layout.update()
        self.update()

    def on_home_all(self):
        self.driver.address.hardware.q.push('home_all')
        
    def on_limits_updated(self):
        low_energy_limit, high_energy_limit = self.driver.limits.read('wn')
        self.low_energy_limit_display.write(low_energy_limit, 'wn')
        self.high_energy_limit_display.write(high_energy_limit, 'wn')
        
    def show_advanced(self):
        pass

    def stop(self):
        pass




### autotune ##################################################################


class BaseOPAAutoTune(QtGui.QWidget):

    def __init__(self, opa):
        QtGui.QWidget.__init__(self)
        self.opa = opa
        self.setLayout(QtGui.QVBoxLayout())
        self.layout = self.layout()
        self.layout.setMargin(0)
        self.initialized = pc.Bool()

    def initialize(self):
        raise NotImplementedError

    def load(self, aqn_path):
        raise NotImplementedError

    def run(self, worker):
        raise NotImplementedError

    def save(self, aqn_path):
        raise NotImplementedError

    def update_channel_names(self, channel_names):
        raise NotImplementedError


### testing ###################################################################


if __name__ == '__main__':
    if True:
        pass
        
        

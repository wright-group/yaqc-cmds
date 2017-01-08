# TODO: record degree of microstepping in data file


### import ####################################################################


from __future__ import absolute_import, division, print_function, unicode_literals

import os
import collections
import time

import numpy as np

import pyvisa

from PyQt4 import QtGui, QtCore

import WrightTools as wt

import project.classes as pc
import project.widgets as pw
import project.project_globals as g
import project.com_handler as com_handler
from project.ini_handler import Ini
main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'hardware', 'filters', 'homebuilt', 'homebuilt.ini'))


### driver ####################################################################


class Driver():

    def __init__(self):
        self.native_units = 'OD'
        # mutex attributes
        self.limits = pc.NumberLimits(0, 4, units=self.native_units)
        self.limits_deg = pc.NumberLimits(-360, 360, units='deg')
        self.current_position = pc.Number(name='OD', initial_value=0.,
                                          limits=self.limits,
                                          units=self.native_units, 
                                          display=True,
                                          set_method='set_position')
        self.offset = pc.Number(initial_value=0, 
                                units=self.native_units, display=True)
        self.current_position_deg = pc.Number(display=True, limits=self.limits_deg, units='deg')
        # objects to be sent to PyCMDS
        self.exposed = [self.current_position]
        self.recorded = collections.OrderedDict()
        # finish
        self.gui = GUI(self)
        self.initialized = pc.Bool()
        
    def _get_color(self):
        # TODO: full implementation, actually refering to OPA color
        wn = float(self.color_string.read())
        color = wt.units.converter(wn, 'wn', 'nm')
        return color

    def close(self):
        self.port.close()
        
    def home(self, inputs=[]):
        self.port.write(' '.join(['H', str(self.index)]))
        self.wait_until_ready()
        self.current_position_deg.write(ini.read('ND'+str(self.index), 'home position (deg)'))
        self.get_position()

    def get_position(self):
        positions = [self._get_color(), self.current_position_deg.read()]
        od = -np.log10(self.calibration.get_value(positions))
        self.current_position.write(od, 'OD')

    def initialize(self, inputs, address):
        self.address = address
        self.index = inputs[0]
        # calibration
        self.calibration_path = pc.Filepath(ini=ini, section='ND'+str(self.index), option='calibration')
        self.calibration_path.updated.connect(self.on_calibration_path_updated)
        self.on_calibration_path_updated()
        self.color_string = pc.String(ini=ini, section='ND'+str(self.index), option='color (wn)')
        # open com port
        port_index = ini.read('main', 'serial port')
        self.port = com_handler.get_com(port_index, timeout=100000)  # timeout in 100 seconds
        # stepping
        self.microsteps = ini.read('main', 'degree of microstepping')
        steps_per_rotation = ini.read('main', 'full steps per rotation') * self.microsteps
        self.degrees_per_step = 360./steps_per_rotation
        self.port.write('U %i'%self.microsteps)
        self.invert = pc.Bool(ini=ini, section='ND'+str(self.index), option='invert')
        # read from ini
        self.home_position = pc.Number(initial_value=ini.read('ND'+str(self.index), 'home position (deg)'),
                                       display=True, limits=self.limits_deg, units='deg')
        self.current_position_deg.write(ini.read('ND'+str(self.index), 'current position (deg)'))
        # recorded
        self.recorded['nd' + str(self.index)] = [self.current_position, self.native_units, 1., '0', False]
        self.recorded['nd%i_position'%self.index] = [self.current_position_deg, 'deg', 1., '0', False]
        self.recorded['nd%i_home'%self.index] = [self.home_position, 'deg', 1., '0', False]
        # finish
        self.get_position()
        self.initialized.write(True)
        self.address.initialized_signal.emit()
        self.wait_until_ready()

    def is_busy(self):
        return False

    def on_calibration_path_updated(self):
        new_path = self.calibration_path.read()
        self.calibration = wt.calibration.from_file(new_path)        
        
    def set_degrees(self, inputs=[]):
        degrees = int(inputs[0])
        change = degrees - self.current_position_deg.read()
        steps = np.floor(change/self.degrees_per_step)
        if self.invert.read():
            signed_steps = steps * -1
        else:
            signed_steps = steps
        command = ' '.join(['M', str(self.index), str(signed_steps)])
        self.port.write(command)
        self.wait_until_ready()
        # update own position
        current_position = self.current_position_deg.read()
        current_position += steps * self.degrees_per_step
        self.current_position_deg.write(current_position)
        
    def set_offset(self, offset):
        self.offset.write(offset, 'OD')
        destination = self.address.hardware.destination.read('OD')
        self.set_position(destination)
        
    def set_position(self, destination):
        color = self._get_color()
        c = 10.**-(destination + self.offset.read())
        d = self.calibration.get_positions(c, color=color)[0]
        print(d)
        self.set_degrees([d['angle']])
        
    def set_zero(self, zero):
        self.zero_position.write(zero)
        # write new position to ini
        section = 'ND{}'.format(self.index)
        option = 'zero position (steps)'
        ini.write(section, option, zero)
        
    def wait_until_ready(self):
        while True:
            command = ' '.join(['Q', str(self.index)])
            status = self.port.write(command, then_read=True).rstrip()
            if status == 'R':
                break
            time.sleep(0.1)
        self.port.flush()


class Driver_offline(Driver):
    
    def initialize(self, inputs, address):
        self.address = address
        # recorded
        self.recorded['w0'] = [self.current_position, self.native_units, 1., '0', False]
        # finish
        self.initialized.write(True)
        self.address.initialized_signal.emit()


### gui #######################################################################


class GUI(QtCore.QObject):

    def __init__(self, driver):
        QtCore.QObject.__init__(self)
        self.driver = driver

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
        # settings container
        settings_container_widget = QtGui.QWidget()
        settings_scroll_area = pw.scroll_area(show_bar=False)
        settings_scroll_area.setWidget(settings_container_widget)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        self.layout.addWidget(settings_scroll_area)
        # offset
        input_table = pw.InputTable()
        input_table.add('Offset', None)
        input_table.add('Value', self.driver.offset)
        settings_layout.addWidget(input_table)
        # calibration
        input_table = pw.InputTable()
        input_table.add('Calibration', None)
        input_table.add('Path', self.driver.calibration_path)
        input_table.add('Color (wn)', self.driver.color_string)
        settings_layout.addWidget(input_table)
        # current position
        input_table = pw.InputTable()
        input_table.add('Position', None)
        input_table.add('Current', self.driver.current_position_deg)
        self.destination_deg = self.driver.current_position_deg.associate(display=False)
        input_table.add('Destination', self.destination_deg)
        input_table.add('Invert', self.driver.invert)
        settings_layout.addWidget(input_table)
        self.set_steps_button = pw.SetButton('SET POSITION')
        settings_layout.addWidget(self.set_steps_button)
        self.set_steps_button.clicked.connect(self.on_set_deg)
        g.queue_control.disable_when_true(self.set_steps_button)
        # home
        input_table = pw.InputTable()
        input_table.add('Home', None)
        input_table.add('Current', self.driver.home_position)
        self.destination_home = self.driver.home_position.associate(display=False)
        input_table.add('Destination', self.destination_home)
        settings_layout.addWidget(input_table)
        self.set_zero_button = pw.SetButton('SET HOME')
        settings_layout.addWidget(self.set_zero_button)
        self.set_zero_button.clicked.connect(self.on_set_home)
        g.queue_control.disable_when_true(self.set_zero_button)
        # home button
        self.home_button = pw.SetButton('SEND HOME', 'advanced')
        settings_layout.addWidget(self.home_button)
        self.home_button.clicked.connect(self.on_home)
        g.queue_control.disable_when_true(self.home_button)
        # finish
        settings_layout.addStretch(1)
        self.layout.addStretch(1)
        self.driver.address.update_ui.connect(self.update)

    def on_home(self):
        self.driver.address.hardware.q.push('home')

    def on_set_deg(self):
        deg = self.destination_deg.read()
        self.driver.address.hardware.q.push('set_degrees', [deg])

    def on_set_home(self):
        # TODO:
        return
        zero = self.destination_zero.read()
        self.driver.set_zero(zero)

    def update(self):
        pass

    def stop(self):
        pass

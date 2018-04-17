# TODO: record degree of microstepping in data file


### import ####################################################################


from __future__ import absolute_import, division, print_function, unicode_literals

import os
import collections
import time

import numpy as np

from PyQt4 import QtGui, QtCore

import WrightTools as wt

import project.classes as pc
import project.widgets as pw
import project.project_globals as g
import hardware.hardware as hw
from hardware.filters.filters import Driver as BaseDriver
from hardware.filters.filters import GUI as BaseGUI
import project.com_handler as com_handler
from project.ini_handler import Ini
main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'hardware', 'filters', 'homebuilt', 'homebuilt.ini'))


### driver ####################################################################


class Driver(BaseDriver):

    def __init__(self, *args, **kwargs):
        BaseDriver.__init__(self, *args, **kwargs)
        self.index = kwargs['index']
        
    def close(self):
        self.port.close()
        
    def home(self, inputs=[]):
        self.port.write(' '.join(['H', str(self.index)]))
        self.wait_until_ready()
        self.motor_position.write(0)
        self.get_position()

    def get_position(self):
        position = (self.motor_position.read() - self.zero_position.read()) * self.native_per_deg * self.factor.read()
        self.position.write(position, 'deg')
        return position

    def initialize(self):
        # open com port
        port_index = ini.read('main', 'serial port')
        self.port = com_handler.get_com(port_index, timeout=100000)  # timeout in 100 seconds
        # stepping
        self.microsteps = ini.read('main', 'degree of microstepping')
        steps_per_rotation = ini.read('main', 'full steps per rotation') * self.microsteps
        self.degrees_per_step = 360. / steps_per_rotation
        self.port.write('U %i' % self.microsteps)
        # read from ini
        self.motor_position.write(ini.read(self.name, 'current position (deg)'))
        # recorded
        self.recorded[self.name] = [self.motor_position, self.native_units, 1., '0', False]

        # finish
        self.initialized.write(True)
        self.initialized_signal.emit()
        self.wait_until_ready()

    def is_busy(self):
        #TODO:
        return False

    def set_degrees(self, degrees):
        change = degrees - self.motor_position.read()
        steps = np.floor(change/self.degrees_per_step)
        signed_steps = steps
        command = ' '.join(['M', str(self.index), str(signed_steps)])
        self.port.write(command)
        self.wait_until_ready()
        # update own position
        motor_position = self.motor_position.read()
        motor_position += steps * self.degrees_per_step
        self.motor_position.write(motor_position)
        self.get_position()
        
    def set_position(self, destination):
        self.set_degrees(self.zero_position.read('deg') + destination / (self.native_per_deg * self.factor.read()))
        
    def set_zero(self, zero):
        self.zero_position.write(zero)
        # write new position to ini
        option = 'zero position (steps)'
        ini.write(self.name, option, zero)
        
    def wait_until_ready(self):
        while True:
            command = ' '.join(['Q', str(self.index)])
            status = self.port.write(command, then_read=True).rstrip()
            if status == 'R':
                break
            time.sleep(0.1)
        self.port.flush()


### gui #######################################################################


class GUI(BaseGUI):
    pass;

#    def __init__(self, driver):
#        QtCore.QObject.__init__(self)
#        self.driver = driver
#
#    def create_frame(self, layout):
#        layout.setMargin(5)
#        self.layout = layout
#        self.frame = QtGui.QWidget()
#        self.frame.setLayout(self.layout)
#        if self.driver.initialized.read():
#            self.initialize()
#        else:
#            self.driver.initialized.updated.connect(self.initialize)
#
#    def initialize(self):
###        # settings container
#        settings_container_widget = QtGui.QWidget()
#        settings_scroll_area = pw.scroll_area(show_bar=False)
#        settings_scroll_area.setWidget(settings_container_widget)
#        settings_container_widget.setLayout(QtGui.QVBoxLayout())
#        settings_layout = settings_container_widget.layout()
#        settings_layout.setMargin(5)
#        self.layout.addWidget(settings_scroll_area)
#        # offset
#        input_table = pw.InputTable()
#        input_table.add('Offset', None)
#        input_table.add('Value', self.driver.offset)
#        settings_layout.addWidget(input_table)
#        # current position
#        input_table = pw.InputTable()
#        input_table.add('Position', None)
#        input_table.add('Current', self.driver.motor_position)
#        self.destination = self.driver.motor_position.associate(display=False)
#        input_table.add('Destination', self.destination)
        #input_table.add('Invert', self.driver.invert)
#        settings_layout.addWidget(input_table)
#        self.set_steps_button = pw.SetButton('SET POSITION')
##        settings_layout.addWidget(self.set_steps_button)
##        self.set_steps_button.clicked.connect(self.on_set)
#        g.queue_control.disable_when_true(self.set_steps_button)
#        # home
        #input_table = pw.InputTable()
        #input_table.add('Home', None)
        #input_table.add('Current', self.driver.home_position)
        #self.destination_home = self.driver.home_position.associate(display=False)
        #input_table.add('Destination', self.destination_home)
        #settings_layout.addWidget(input_table)
#        self.set_zero_button = pw.SetButton('SET HOME')
#        settings_layout.addWidget(self.set_zero_button)
#        self.set_zero_button.clicked.connect(self.on_set_home)
#        g.queue_control.disable_when_true(self.set_zero_button)
#        # home button
#        self.home_button = pw.SetButton('SEND HOME', 'advanced')
#        settings_layout.addWidget(self.home_button)
#        self.home_button.clicked.connect(self.on_home)
#        g.queue_control.disable_when_true(self.home_button)
#        # finish
#        settings_layout.addStretch(1)
#        self.layout.addStretch(1)
#        #self.driver.address.update_ui.connect(self.update)
#
#    #def on_home(self):
#    #    self.driver.address.hardware.q.push('home')
#
#    #def on_set(self):
#    #    deg = self.destination.read()
#    #    self.driver.address.hardware.q.push('set_degrees', [deg])
##
#    def on_set_home(self):
#        # TODO:
#        return
#        zero = self.destination_zero.read()
#        self.driver.set_zero(zero)
#
#    def update(self):
#        pass
##
#    def stop(self):
####        pass

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
    pass

### import ####################################################################


import time

import numpy as np

from PyQt4 import QtGui, QtCore

import project.classes as pc
import project.widgets as pw
import project.project_globals as g
from project.ini_handler import Ini
from hardware.delays.delays import Driver as BaseDriver
from hardware.delays.delays import GUI as BaseGUI
import project.com_handler as com_handler


### define ####################################################################


main_dir = g.main_dir.read()


### driver ####################################################################


class Driver(BaseDriver):

    def __init__(self, *args, **kwargs):
        self.com_channel = kwargs.pop('port')
        kwargs['native_units'] = 'ps'
        self.index = kwargs.pop('index')
        self.native_per_mm = 6.671281903963041
        BaseDriver.__init__(self, *args, **kwargs)

    def close(self):
        self.port.close()

    def get_motor_position(self):
        p = self.port.write('G', then_read=True)
        print('GET MOTOR POSITION', p)

    def get_position(self):
        position = self.get_motor_position()
        # calculate delay
        delay = (position - self.zero_position.read()) * self.native_per_mm * self.factor.read()
        self.position.write(delay, self.native_units)
        # return
        return delay

    def initialize(self):
        self.port = com_handler.get_com(self.com_channel)   
        self.motor_limits.write(0, 250, 'mm')

    def is_busy(self):
        # TODO:
        return False

    def set_position(self, destination):
        destination_mm = self.zero_position.read() + destination/(self.native_per_mm * self.factor.read())
        self.set_motor_position(destination_mm)

    def set_motor_position(self, motor_position):
        command = 'A %f'%motor_position
        self.port.write(command)
        BaseDriver.set_motor_position(self, motor_position)


### gui #######################################################################


class GUI(BaseGUI):
    pass

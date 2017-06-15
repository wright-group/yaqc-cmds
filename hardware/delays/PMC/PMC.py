### import ####################################################################


import os
import collections
import time

from PyQt4 import QtGui, QtCore

import WrightTools as wt

import project
import project.classes as pc
import project.widgets as pw
import project.project_globals as g
from hardware.delays.delays import Driver as BaseDriver
from hardware.delays.delays import GUI as BaseGUI
import project.precision_micro_motors.precision_motors as motors


### define ####################################################################


main_dir = g.main_dir.read()
ini = project.ini_handler.Ini(os.path.join(main_dir, 'hardware', 'delays',
                                                     'PMC', 'PMC.ini'))

ps_per_mm = 6.671281903963041  # a mm on the delay stage (factor of 2)


### driver ####################################################################


class Driver(BaseDriver):

    def __init__(self, *args, **kwargs):
        self.index = kwargs['index']
        self.native_per_mm = ps_per_mm
        BaseDriver.__init__(self, *args, **kwargs)

    def close(self):
        self.motor.close()

    def get_position(self):
        position = self.motor.current_position_mm
        self.motor_position.write(position, 'mm')
        delay = (position - self.zero_position.read()) * ps_per_mm * self.factor.read()
        self.position.write(delay, 'ps')
        return delay

    def initialize(self):
        motor_identity = motors.identity['D{}'.format(self.index)]
        self.motor = motors.Motor(motor_identity)
        self.current_position_mm = pc.Number(units='mm', display=True, decimals=5)
        # factor
        self.factor = pc.Number(name='Factor', ini=ini, section='D%s'%self.index, option='factor', decimals=0)
        # zero position
        zero = ini.read('D%i'%self.index, 'zero position (mm)')
        self.zero_position.write(zero, 'mm')
        # finish
        self.get_position()
        self.initialized.write(True)
        self.initialized_signal.emit()

    def is_busy(self):
        return not self.motor.is_stopped()

    def set_position(self, destination):
        destination_mm = self.zero_position.read() + destination/(ps_per_mm * self.factor.read())
        self.set_motor_position(destination_mm)
    
    def set_motor_position(self, destination):
        self.motor.move_absolute(destination, 'mm')
        self.motor.wait_until_still(method=self.get_position)
        self.get_position()

    def set_zero(self, zero):
        self.zero_position.write(zero)
        min_value = -self.zero_position.read() * ps_per_mm * self.factor.read()
        max_value = (50. - self.zero_position.read()) * ps_per_mm * self.factor.read()
        self.limits.write(min_value, max_value, 'ps')
        self.get_position()
        # write new position to ini
        section = 'D{}'.format(self.index)
        option = 'zero position (mm)'
        ini.write(section, option, zero)


### gui #######################################################################


class GUI(BaseGUI):
    pass

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

    def close(self):
        self.motor.close()

    def get_position(self):
        position = self.motor.current_position_mm
        self.motor_position.write(position, 'mm')
        delay = (position - self.zero_position.read()) * ps_per_mm * self.factor.read()
        self.position.write(delay, 'ps')
        return delay

    def initialize(self, index):
        self.index = index
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


class PLACEHOLDER(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)
        # list of objects to be exposed to PyCMDS
        self.native_units = 'ps'
        self.limits = pc.NumberLimits(min_value=-100, max_value=100, units='ps')
        self.current_position = pc.Number(name='Delay', initial_value=0.,
                                          limits=self.limits,
                                          units='ps', display=True,
                                          set_method='set_position')
        self.offset = pc.Number(initial_value=0, units=self.native_units, display=True)
        self.motor_limits = pc.NumberLimits(min_value=0, max_value=50, units='mm')
        self.exposed = [self.current_position]
        self.recorded = collections.OrderedDict()
        self.gui = gui(self)
        self.initialized = pc.Bool()




        
    def set_offset(self, offset):
        # update zero
        offset_from_here = offset - self.offset.read('ps')
        offset_mm = offset_from_here/(ps_per_mm*self.factor.read())
        new_zero = self.zero_position.read('mm') + offset_mm
        self.set_zero(new_zero)
        self.offset.write(offset)
        # return to old position
        destination = self.address.hardware.destination.read('ps')
        self.set_position(destination)






### gui #######################################################################


class GUI(BaseGUI):
    pass

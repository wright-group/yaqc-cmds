### import ####################################################################


import os
import collections
import time

import numpy as np

from PyQt4 import QtGui, QtCore

import project.com_handler as com_handler
import project.classes as pc
import project.widgets as pw
import project.project_globals as g
from project.ini_handler import Ini
from hardware.delays.delays import Driver as BaseDriver
from hardware.delays.delays import GUI as BaseGUI


### define ####################################################################


main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'hardware', 'delays',
                                 'MFA',
                                 'MFA.ini'))


### define ####################################################################


# TODO: move com channel to .ini
COM_channel = 4

error_dict = {'0': None,
              '@': None,
              'A': 'Unknown message code or floating point controller address [A]',
              'B': 'Controller address not correct [B]',
              'C': 'Parameter missing or out of range [C]',
              'D': 'Command not allowed [D]',
              'E': 'Home sequence already started [E]',
              'F': 'ESP stage name unknown [F]',
              'G': 'Displacement out of limits [G]',
              'H': 'Command not allowed in NOT REFERENCED state [H]',
              'I': 'Command not allowed in CONFIGURATION state [I]',
              'J': 'Command not allowed in DISABLE state [J]',
              'K': 'Command not allowed in READY state [K]',
              'L': 'Command not allowed in HOMING state [L]',
              'M': 'Command not allowed in MOVING state [M]',
              'N': 'Current position out of software limit [N]',
              'S': 'Communication time-out [S]',
              'U': 'Error during EEPROM access [U]',
              'V': 'Error during command execution [V]',
              'W': 'Command not allowed for PP version [W]',
              'X': 'Command not allowed for CC version [X]'}
              
status_dict = {'READY from MOVING': '33',
               'READY from HOMING': '1E',
               'MOVING': '28',
               'NOT REF from RESET': '0A',
               '????': 'P-'}
              
fs_per_mm = 6000.671281903963041  # a mm on the delay stage (factor of 2)


### driver ####################################################################


class Driver(BaseDriver):

    def __init__(self, *args, **kwargs):
        self.index = kwargs.pop('index')
        self.native_per_mm = fs_per_mm
        super(self.__class__, self).__init__(*args, **kwargs)
        self.motor_limits = pc.NumberLimits(0, 25, 'mm')
        
    def _tell_status(self):
        # read
        status = self.port.write(str(self.axis)+'TS', then_read=True)
        # process
        status = str(status).split('TS')[1]
        out = {}
        out['error'] = status[:4]
        out['state'] = status[4:6]
        return out

    def close(self):
        self.port.close()

    def get_position(self):
        # read
        position = self.port.write(str(self.axis)+'TP', then_read=True)
        # proccess (mm)
        position = float(str(position).split('TP')[1])
        self.motor_position.write(position, 'mm')
        # calculate delay (fs)
        delay = (position - self.zero_position.read()) * fs_per_mm * self.factor.read()
        self.position.write(delay, 'fs')
        # return
        return delay
        
    def home(self, inputs=[]):
        self.port.write(unicode(str(self.axis)+'OR'))
        while not self._tell_status()['state'] == status_dict['READY from HOMING']:
            time.sleep(0.01)
            self.get_position()

    def initialize(self):
        self.axis = ini.read('D' + str(self.index), 'axis')
        # load communications channel
        self.port = com_handler.get_com(COM_channel)
        # read from ini
        self.factor = pc.Number(ini=ini, section='D{}'.format(self.index), option='factor', decimals=0, disable_under_queue_control=True)
        self.factor.updated.connect(self.on_factor_updated)        
        self.zero_position = pc.Number(name='Zero', initial_value=12.5,
                                       ini=ini, section='D{}'.format(self.index),
                                       option='zero position (mm)', import_from_ini=True,
                                       save_to_ini_at_shutdown=True,
                                       limits=self.motor_limits,
                                       decimals=5,
                                       units='mm', display=True)                                   
        self.set_zero(self.zero_position.read())
        self.label = pc.String(ini=ini, section='D{}'.format(self.index), option='label', disable_under_queue_control=True)
        self.label.updated.connect(self.update_recorded)
        self.update_recorded()
        # finish
        self.get_position()
        self.initialized.write(True)
        self.initialized_signal.emit()

    def is_busy(self):
        return False
        
    def on_factor_updated(self):
        if self.factor.read() == 0:
            self.factor.write(1)
        # record factor
        self.factor.save()
        # update limits
        min_value = -self.zero_position.read() * fs_per_mm * self.factor.read()
        max_value = (25. - self.zero_position.read()) * fs_per_mm * self.factor.read()
        self.limits.write(min_value, max_value, 'fs')
        
    def set_offset(self, offset):
        # update zero
        offset_from_here = offset - self.offset.read('fs')
        offset_mm = offset_from_here/(fs_per_mm*self.factor.read())
        new_zero = self.zero_position.read('mm') + offset_mm
        self.set_zero(new_zero)
        self.offset.write(offset)
        # return to old position
        destination = self.address.hardware.destination.read('fs')
        self.set_position(destination)       
        
    def set_position(self, destination):
        # get destination_mm
        destination_mm = self.zero_position.read() + destination/(fs_per_mm * self.factor.read())
        self.set_motor_position(destination_mm)
        
    def set_motor_position(self, motor_position):
        """
        motor_position in mm
        """
        # move hardware
        # TODO: consider backlash correction? 
        self.port.write(unicode(str(self.axis)+'PA'+str(motor_position)))
        while not self._tell_status()['state'] == status_dict['READY from MOVING']:
            time.sleep(0.01)
            self.get_position()
        # get final position
        self.get_position()
        
    def set_zero(self, zero):
        self.zero_position.write(zero)
        min_value = -self.zero_position.read() * fs_per_mm * self.factor.read()
        max_value = (25. - self.zero_position.read()) * fs_per_mm * self.factor.read()
        self.limits.write(min_value, max_value, 'fs')
        # write new position to ini
        section = 'D{}'.format(self.index)
        option = 'zero position (mm)'
        ini.write(section, option, zero)
        
    def update_recorded(self):
        self.recorded.clear()
        self.recorded['d' + str(self.index)] = [self.position, self.native_units, 1., self.label.read(), False]
        self.recorded['d' + str(self.index) + '_position'] = [self.motor_position, 'mm', 1., self.label.read(), False]
        self.recorded['d' + str(self.index) + '_zero'] = [self.zero_position, 'mm', 1., self.label.read(), False] 


### gui #######################################################################


class GUI(BaseGUI):
    pass

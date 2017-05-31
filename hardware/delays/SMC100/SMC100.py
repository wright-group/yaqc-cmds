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
from hardware.delays.delays import Driver, GUI


### define ####################################################################


main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'hardware', 'delays',
                                 'SMC100',
                                 'SMC100.ini'))


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


class Driver(Driver):

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.native_units = 'fs'        
        # mutex attributes
        self.limits = pc.NumberLimits(units=self.native_units)
        self.motor_limits = pc.NumberLimits(min_value=0, max_value=25, units='mm')
        self.current_position = pc.Number(name='Delay', initial_value=0.,
                                          limits=self.limits,
                                          units=self.native_units, 
                                          display=True,
                                          set_method='set_position')
        self.offset = pc.Number(initial_value=0, 
                                units=self.native_units, display=True)
        self.current_position_mm = pc.Number(units='mm', display=True, decimals=5)
        # objects to be sent to PyCMDS
        self.exposed = [self.current_position]
        self.recorded = collections.OrderedDict()
        self.initialized = pc.Bool()
        
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
        self.current_position_mm.write(position, 'mm')
        # calculate delay (fs)
        delay = (position - self.zero_position.read()) * fs_per_mm * self.factor.read()
        self.current_position.write(delay, 'fs')
        # return
        return delay
        
    def home(self, inputs=[]):
        self.port.write(unicode(str(self.axis)+'OR'))
        while not self._tell_status()['state'] == status_dict['READY from HOMING']:
            time.sleep(0.01)
            self.get_position()

    def initialize(self, inputs):
        self.index = inputs[0]
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
        self.set_position_mm([destination_mm])
        
    def set_position_mm(self, inputs):
        destination = inputs[0]
        # move hardware
        # TODO: consider backlash correction? 
        self.port.write(unicode(str(self.axis)+'PA'+str(destination)))
        while not self._tell_status()['state'] == status_dict['READY from MOVING']:
            time.sleep(0.01)
            self.get_position()
        # get position
        self.get_position()
        # get position
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
        self.recorded['d' + str(self.index)] = [self.current_position, self.native_units, 1., self.label.read(), False]
        self.recorded['d' + str(self.index) + '_position'] = [self.current_position_mm, 'mm', 1., self.label.read(), False]
        self.recorded['d' + str(self.index) + '_zero'] = [self.zero_position, 'mm', 1., self.label.read(), False] 


### gui #######################################################################


class GUI(GUI):

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
        # settings
        input_table = pw.InputTable()
        input_table.add('Settings', None)
        input_table.add('Label', self.driver.label)
        input_table.add('Factor', self.driver.factor)
        # mm input table
        input_table.add('Position', None)
        input_table.add('Current', self.driver.current_position_mm)
        self.mm_destination = self.driver.current_position_mm.associate(display=False)
        input_table.add('Destination', self.mm_destination)
        self.scroll_layout.addWidget(input_table)
        # set mm button
        self.set_mm_button = pw.SetButton('SET POSITION')
        self.scroll_layout.addWidget(self.set_mm_button)
        self.set_mm_button.clicked.connect(self.on_set_mm)
        g.queue_control.disable_when_true(self.set_mm_button)
        # zero input table
        input_table = pw.InputTable()
        input_table.add('Zero', None)
        input_table.add('Current', self.driver.zero_position)
        self.zero_destination = self.driver.zero_position.associate(display=False)
        input_table.add('Destination', self.zero_destination)
        self.scroll_layout.addWidget(input_table)
        # set zero button
        self.set_zero_button = pw.SetButton('SET ZERO')
        self.scroll_layout.addWidget(self.set_zero_button)
        self.set_zero_button.clicked.connect(self.on_set_zero)
        g.queue_control.disable_when_true(self.set_zero_button)
        # horizontal line
        self.scroll_layout.addWidget(pw.line('H'))
        # home button
        input_table = pw.InputTable()
        self.home_button = pw.SetButton('HOME', 'advanced')
        self.scroll_layout.addWidget(self.home_button)
        self.home_button.clicked.connect(self.on_home)
        g.queue_control.disable_when_true(self.home_button)
        # finish
        self.scroll_layout.addStretch(1)
        self.layout.addStretch(1)
        self.driver.address.update_ui.connect(self.update)
        
    def on_home(self):
        self.driver.address.hardware.q.push('home')
        
    def on_set_mm(self):
        new_mm = self.mm_destination.read('mm')
        new_mm = np.clip(new_mm, 1e-3, 300-1e-3)
        self.driver.address.hardware.q.push('set_position_mm', [new_mm])
        
    def on_set_zero(self):
        new_zero = self.zero_destination.read('mm')
        self.driver.set_zero(new_zero)
        self.driver.offset.write(0)
        name = self.driver.address.hardware.name
        g.coset_control.read().zero(name)

    def update(self):
        pass

    def stop(self):
        pass


### testing ###################################################################


if __name__ == '__main__':
    pass

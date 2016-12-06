### import ####################################################################


from __future__ import absolute_import, division, print_function, unicode_literals

import os
import collections
import time

import numpy as np

from PyQt4 import QtGui, QtCore

import project.classes as pc
import project.widgets as pw
import project.project_globals as g
import project.com_handler as com_handler
from project.ini_handler import Ini
main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'hardware', 'delays', 'Dynacron', 'dynacron.ini'))

### define ####################################################################

ps_per_mm = 6.671281903963041  # a mm on the delay stage (factor of 2)

### driver ####################################################################


class Driver():

    def __init__(self):
        self.native_units = 'ps'
        # mutex attributes
        self.limits = pc.NumberLimits(units=self.native_units)
        self.limits_mm = pc.NumberLimits(0, 250, units='mm')
        self.current_position = pc.Number(name='Delay', initial_value=0.,
                                          limits=self.limits,
                                          units=self.native_units, 
                                          display=True,
                                          set_method='set_position')    
        self.offset = pc.Number(initial_value=0, 
                                units=self.native_units, display=True)
        self.current_position_mm = pc.Number(display=True, decimals=3, limits=self.limits_mm)
        # objects to be sent to PyCMDS
        self.exposed = [self.current_position]
        self.recorded = collections.OrderedDict()
        # finish
        self.gui = GUI(self)
        self.initialized = pc.Bool()

    def close(self):
        self.port.close()
        
    def home(self):
        self.port.write('H')
        self.wait_until_ready()
        self.current_position_mm.write(0)
        self.get_position()

    def get_position(self):
        difference_mm = self.current_position_mm.read() - self.zero_position_mm.read()
        ps = difference_mm * ps_per_mm * self.factor.read()
        #self.current_position.write(ps, 'ps')
        return ps

    def initialize(self, inputs, address):
        self.address = address
        #self.index = inputs[0]
        # open com port
        port_index = ini.read('main', 'serial port')
        self.port = com_handler.get_com(port_index, timeout=10000)
        # read from ini
        self.zero_position_mm = pc.Number(initial_value=ini.read('Delay', 'zero position (mm)'),
                                       display=True, limits=self.limits_mm, decimals=3)
        self.set_zero(self.zero_position_mm.read())
        self.current_position_mm.write(ini.read('Delay', 'current position (mm)'))
        # recorded
        # TODO Blaise, check the next three lines.
        self.recorded['dynacron'] = [self.current_position, self.native_units, 1., '0', False]
        self.recorded['dynacron_position'] = [self.current_position_mm, 'mm', 1., '0', False]
        self.recorded['dynacron_zero'] = [self.zero_position_mm, 'mm', 1., '0', False]
        # finish
        self.get_position()
        self.initialized.write(True)
        self.address.initialized_signal.emit()

    def is_busy(self):
        return False
        # TODO rewrite this method 
    def set_offset(self, offset):
        # update zero
        offset_from_here = offset - self.offset.read('OD')
        offset_steps = offset_from_here*100/np.log10(np.abs(self.fraction_per_100.read()))
        new_zero = self.zero_position.read() + int(offset_steps)
        self.set_zero(new_zero)
        self.offset.write(offset)
        # return to old position
        destination = self.address.hardware.destination.read('OD')
        self.set_position(destination)       
        
    def set_position(self, destination):        
        time = zero_position_mm.read() * ps_per_mm * self.factor.read() - destination
        distance = time/ps_per_mm/self.factor.read()        
        self.set_distance(distance)
        
    def set_distance(self, distance):
        old_mm = current_position_mm.read()
        new_mm = current_position_mm.read() + distance
        command = ' '.join(['M', str(distance)])
        self.port.write(command)
        self.wait_until_ready()
        self.current_position_mm.write(new_mm)
        section = 'Delay'
        option = 'current position (mm)'
        ini.write(section, option, self.current_position_mm.read())
        # get position (ps)
        self.get_position()

     # TODO rewrite this method    
    def set_zero(self, zero):
        self.zero_position.write(zero)
        # write new position to ini
        section = 'Delay'
        option = 'zero position (mm)'
        ini.write(section, option, zero)
    
    # TODO rewrite this method   
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
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        self.layout.addWidget(settings_scroll_area)
        # position
        input_table = pw.InputTable()
        input_table.add('Position', None)
        input_table.add('Current', self.driver.current_position_steps)
        self.destination_steps = self.driver.current_position_steps.associate(display=False)
        input_table.add('Destination', self.destination_steps)
        settings_layout.addWidget(input_table)
        self.set_steps_button = pw.SetButton('SET POSITION')
        settings_layout.addWidget(self.set_steps_button)
        self.set_steps_button.clicked.connect(self.on_set_steps)
        g.queue_control.disable_when_true(self.set_steps_button)
        # zero
        input_table = pw.InputTable()
        input_table.add('Zero', None)
        input_table.add('Current', self.driver.zero_position)
        self.destination_zero = self.driver.zero_position.associate(display=False)
        input_table.add('Destination', self.destination_zero)
        settings_layout.addWidget(input_table)
        self.set_zero_button = pw.SetButton('SET ZERO')
        settings_layout.addWidget(self.set_zero_button)
        self.set_zero_button.clicked.connect(self.on_set_zero)
        g.queue_control.disable_when_true(self.set_zero_button)
        # fraction per 100
        input_table = pw.InputTable()
        input_table.add('Fraction per 100', None)
        input_table.add('Current', self.driver.fraction_per_100)
        self.destination_fraction = self.driver.fraction_per_100.associate(display=False)
        input_table.add('Destination', self.destination_fraction)
        settings_layout.addWidget(input_table)
        self.set_fraction_button = pw.SetButton('SET FRACTION')
        settings_layout.addWidget(self.set_fraction_button)
        self.set_fraction_button.clicked.connect(self.on_set_fraction)
        g.queue_control.disable_when_true(self.set_fraction_button)
        # horizontal line
        settings_layout.addWidget(pw.line('H'))
        # home button
        self.home_button = pw.SetButton('HOME', 'advanced')
        settings_layout.addWidget(self.home_button)
        self.home_button.clicked.connect(self.on_home)
        g.queue_control.disable_when_true(self.home_button)
        # finish
        settings_layout.addStretch(1)
        self.layout.addStretch(1)
        self.driver.address.update_ui.connect(self.update)

    def on_home(self):
        self.driver.address.hardware.q.push('home')

    def on_set_fraction(self):
        fraction = self.destination_fraction.read()
        self.driver.address.hardware.q.push('set_fraction', [fraction])     

    def on_set_steps(self):
        steps = self.destination_steps.read()
        self.driver.address.hardware.q.push('set_steps', [steps])

    def on_set_zero(self):
        zero = self.destination_zero.read()
        self.driver.set_zero(zero)

    def update(self):
        pass

    def stop(self):
        pass

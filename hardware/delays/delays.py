### import ####################################################################


import os
import imp
import time
import collections

import numpy as np

from PyQt4 import QtGui

import WrightTools as wt

import project.project_globals as g
main_dir = g.main_dir.read()
app = g.app.read()
import project.widgets as pw
import project.classes as pc
import hardware.hardware as hw


### define ####################################################################


directory = os.path.dirname(os.path.abspath(__file__))
ini = wt.kit.INI(os.path.join(directory, 'delays.ini'))


### driver ####################################################################


class Driver(hw.Driver):
    
    def __init__(self, *args, **kwargs):
        kwargs['native_units'] = 'ps'
        hw.Driver.__init__(self, *args, **kwargs)
        self.position.write(0.)
        self.motor_position = self.hardware.motor_position
        
    def set_motor_position(self, inputs):
        self.motor_position.write(inputs[0])


### gui #######################################################################


class GUI(hw.GUI):

    def initialize(self):
        self.layout.addWidget(self.scroll_area)
        # attributes
        self.attributes_table.add('Label', self.hardware.label)
        self.attributes_table.add('Factor', self.hardware.factor)
        self.scroll_layout.addWidget(self.attributes_table)
        # mm input table
        input_table = pw.InputTable()
        input_table.add('Position', None)
        input_table.add('Current', self.hardware.motor_position)
        self.motor_destination = self.hardware.motor_position.associate(display=False)
        input_table.add('Destination', self.motor_destination)
        self.scroll_layout.addWidget(input_table)
        # set mm button
        self.set_motor_button = pw.SetButton('SET POSITION')
        self.scroll_layout.addWidget(self.set_motor_button)
        self.set_motor_button.clicked.connect(self.on_set_motor)
        g.queue_control.disable_when_true(self.set_motor_button)
        # zero input table
        input_table = pw.InputTable()
        input_table.add('Zero', None)
        input_table.add('Current', self.hardware.zero_position)
        self.zero_destination = self.hardware.zero_position.associate(display=False)
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
        self.hardware.update_ui.connect(self.update)
        
    def on_home(self):
        self.driver.address.hardware.q.push('home')
        
    def on_set_motor(self):
        new_mm = self.motor_destination.read('mm')
        self.driver.address.hardware.q.push('set_motor_position', [new_mm])
        
    def on_set_zero(self):
        new_zero = self.zero_destination.read('mm')
        self.driver.set_zero(new_zero)
        self.driver.offset.write(0)
        name = self.driver.address.hardware.name
        g.coset_control.read().zero(name)

    def update(self):
        pass


### hardware ##################################################################


class Hardware(hw.Hardware):
    
    def __init__(self, *arks, **kwargs):
        self.kind = 'delay'        
        self.factor = pc.Number(1)
        self.motor_position = pc.Number(units='mm', display=True)
        self.zero_position = pc.Number(display=True)
        hw.Hardware.__init__(self, *arks, **kwargs)
        self.label = pc.String(self.name, display=True)


### initialize ################################################################


hardwares = []    
for name in ini.sections:
    if ini.read(name, 'enable'):
        model = ini.read(name, 'model')
        if model == 'Virtual':
            hardware = Hardware(Driver, [None], GUI, name=name, model='Virtual')
        else:
            path = os.path.abspath(ini.read(name, 'path'))
            fname = os.path.basename(path).split('.')[0]
            mod = imp.load_source(fname, path)
            cls = getattr(mod, 'Driver')
            args = ini.read(name, 'initialization arguments')
            gui = getattr(mod, 'GUI')
            hardware = Hardware(cls, args, gui, name=name, model=model)
        hardwares.append(hardware)
gui = pw.HardwareFrontPanel(hardwares, name='Delays')
advanced_gui = pw.HardwareAdvancedPanel(hardwares, gui.advanced_button)

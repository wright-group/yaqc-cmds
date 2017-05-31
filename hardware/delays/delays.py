### import ####################################################################


import os
import imp
import time
import collections

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


### gui #######################################################################


class GUI(hw.GUI):

    def initialize(self):
        print('DELAY GUI INITIALIZE')  # TODO: remove
        # settings container
        # settings
        input_table = pw.InputTable()
        input_table.add('Settings', None)
        input_table.add('Label', self.hardware.label)
        input_table.add('Factor', self.hardware.factor)
        # mm input table
        input_table.add('Position', None)
        input_table.add('Current', self.hardware.position_mm)
        self.mm_destination = self.hardware.position_mm.associate(display=False)
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


### hardware ##################################################################


class Hardware(hw.Hardware):
    
    def __init__(self, *arks, **kwargs):
        self.kind = 'delay'
        hw.Hardware.__init__(self, *arks, **kwargs)
        self.label = pc.String(self.name, display=True)
        self.factor = pc.Number(1)
        self.position_mm = pc.Number(units='mm', display=True)
        self.zero_position = pc.Number(display=True)


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

### import ####################################################################


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
ini = Ini(os.path.join(main_dir, 'nds',
                                 'homebuilt wheels',
                                 'homebuilt_NDs.ini'))


### driver ####################################################################


class Driver():

    def __init__(self):
        self.native_units = 'OD'
        # mutex attributes
        self.limits = pc.NumberLimits(-1, 4, units=self.native_units)
        self.limits_steps = pc.NumberLimits(-2500, 2500)
        self.current_position = pc.Number(name='OD', initial_value=0.,
                                          limits=self.limits,
                                          units=self.native_units, 
                                          display=True,
                                          set_method='set_position')
        self.offset = pc.Number(initial_value=0, 
                                units=self.native_units, display=True)
        self.current_position_steps = pc.Number(display=True, decimals=0, limits=self.limits_steps)
        # objects to be sent to PyCMDS
        self.exposed = [self.current_position]
        self.recorded = collections.OrderedDict()
        # finish
        self.gui = GUI(self)
        self.initialized = pc.Bool()

    def close(self):
        self.port.close()
        
    def home(self, inputs=[]):
        # first go to steps = 1000
        self.set_steps([1000])
        # now home
        self.port.flush()
        command = ' '.join(['H', str(self.index)])
        self.port.write(command)
        done = False
        while not done:
            recieved = self.port.read()  # unicode
            recieved = str(recieved).rstrip()
            if 'ready' in recieved:
                done = True
        self.port.flush()
        time.sleep(0.25)
        self.current_position_steps.write(0)
        self.get_position()

    def get_position(self):
        difference_steps = self.current_position_steps.read() - self.zero_position.read()
        fraction = self.fraction_per_100.read()
        od = difference_steps * (-np.sign(fraction)*np.log10(np.abs(fraction))/100.)
        self.current_position.write(od, 'OD')
        return od

    def initialize(self, inputs, address):
        self.address = address
        self.index = inputs[0]
        # open com port
        port_index = ini.read('main', 'serial port')
        self.port = com_handler.get_com(port_index, timeout=30000)
        # read from ini
        self.zero_position = pc.Number(initial_value=ini.read('ND'+str(self.index), 'zero position (steps)'),
                                       display=True, limits=self.limits_steps, decimals=0)
        self.set_zero(self.zero_position.read())
        limits_fraction_per_100 = pc.NumberLimits(-1, 1)
        self.fraction_per_100 = pc.Number(initial_value=ini.read('ND'+str(self.index), 'fraction per 100'),
                                          display=True, limits=limits_fraction_per_100)
        self.current_position_steps.write(ini.read('ND'+str(self.index), 'current position (steps)'))
        # recorded
        self.recorded['nd' + str(self.index)] = [self.current_position, self.native_units, 1., '0', False]
        # finish
        self.get_position()
        self.initialized.write(True)
        self.address.initialized_signal.emit()

    def is_busy(self):
        return False
        
    def set_fraction(self, inputs=[]):
        fraction = inputs[0]
        self.fraction_per_100.write(fraction)
        # write new fraction to ini
        section = 'ND{}'.format(self.index)
        option = 'fraction per 100'
        ini.write(section, option, fraction)
        # get position (OD)
        self.get_position()

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
        steps = (100*destination/np.log10(np.abs(self.fraction_per_100.read())))+self.zero_position.read()
        self.set_steps([steps])
        
    def set_steps(self, inputs=[]):
        steps = int(inputs[0])
        steps_from_here = steps - self.current_position_steps.read()
        command = ' '.join(['M', str(self.index), str(steps_from_here)])
        #self.port.flush()
        self.port.write(command)
        done = False
        while not done:
            recieved = self.port.read()  # unicode
            recieved = str(recieved).rstrip()
            if 'ready' in recieved:
                done = True
        self.port.flush()
        time.sleep(0.25)
        # record current position (steps)
        self.current_position_steps.write(steps)
        section = 'ND{}'.format(self.index)
        option = 'current position (steps)'
        ini.write(section, option, self.current_position_steps.read())
        # get position (OD)
        self.get_position()
        
    def set_zero(self, zero):
        self.zero_position.write(zero)
        # write new position to ini
        section = 'ND{}'.format(self.index)
        option = 'zero position (steps)'
        ini.write(section, option, zero)


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
        g.module_advanced_widget.add_child(self.frame)
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
        g.module_control.disable_when_true(self.set_steps_button)
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
        g.module_control.disable_when_true(self.set_zero_button)
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
        g.module_control.disable_when_true(self.set_fraction_button)
        # horizontal line
        settings_layout.addWidget(pw.line('H'))
        # home button
        self.home_button = pw.SetButton('HOME')
        settings_layout.addWidget(self.home_button)
        self.home_button.clicked.connect(self.on_home)
        g.module_control.disable_when_true(self.home_button)
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


### testing ###################################################################

if __name__ == '__main__':
    import pyvisa
    
    resource_manager = pyvisa.ResourceManager()
    instrument = resource_manager.open_resource('ASRL%i::INSTR'%11)
    instrument.baud_rate = 57600
    instrument.end_input = pyvisa.constants.SerialTermination.termination_char
    instrument.timeout = 5000
    

    for _ in range(4):
        
        instrument.flush(pyvisa.constants.VI_IO_IN_BUF)
        instrument.flush(pyvisa.constants.VI_IO_OUT_BUF)
    
        instrument.write('M 1 200')
        done = False
        print 'written'
        
        import WrightTools as wt
        
        with wt.kit.Timer():
        
            while not done:
                recieved = instrument.read()  # unicode
                recieved = str(recieved).rstrip()
                if recieved == 'ready':
                    done = True
            
        time.sleep(0.25)
        print 'done'
        print ''


    print 'hello'
    instrument.close()
    
    
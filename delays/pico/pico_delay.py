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
main_dir = g.main_dir.read()
ini = project.ini_handler.Ini(os.path.join(main_dir, 'delays',
                                                     'pico',
                                                     'pico_delay.ini'))

if g.offline.read():
    import project.precision_micro_motors.v_precision_motors as motors
else:
    import project.precision_micro_motors.precision_motors as motors

ps_per_mm = 6.671281903963041 # a mm on the delay stage (factor of 2)


### delay object ##############################################################


class Delay(QtCore.QObject):

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

    def close(self):
        self.motor.close()

    def get_position(self):
        position = self.motor.get_position('mm')
        self.current_position_mm.write(position, 'mm')
        delay = (position - self.zero_position.read()) * ps_per_mm
        self.current_position.write(delay, 'ps')
        return delay

    def initialize(self, inputs, address):
        self.address = address
        self.index = inputs[0]
        motor_identity = motors.identity['D{}'.format(self.index)]
        self.motor = motors.Motor(motor_identity)
        self.current_position_mm = pc.Number(units='mm', display=True, decimals=5)
        # zero position
        self.zero_position = pc.Number(name='Zero', initial_value=25.,
                                       ini=ini, section='D{}'.format(self.index),
                                       option='zero position (mm)', import_from_ini=True,
                                       save_to_ini_at_shutdown=False,
                                       limits=self.motor_limits,
                                       decimals=5,
                                       units='mm', display=True)
        self.set_zero(self.zero_position.read())
        # recorded
        labels = ['13', '23']
        self.recorded['d%d'%self.index] = [self.current_position, 'ps', 0.01, labels[self.index-1], False]
        self.recorded['d%d_zero'%self.index] = [self.zero_position, 'mm', 0.001, str(self.index), True]
        self.initialized.write(True)
        self.address.initialized_signal.emit()

    def is_busy(self):
        return not self.motor.is_stopped()
        
    def set_offset(self, offset):
        # update zero
        offset_from_here = offset - self.offset.read('ps')
        offset_mm = offset_from_here/ps_per_mm
        new_zero = self.zero_position.read('mm') + offset_mm
        self.set_zero(new_zero)
        self.offset.write(offset)
        # return to old position
        destination = self.address.hardware.destination.read('ps')
        self.set_position(destination)

    def set_position(self, destination):
        destination_mm = self.zero_position.read() + destination/ps_per_mm
        self.motor.move_absolute(destination_mm, 'mm')
        if g.module_control.read():
            self.motor.wait_until_still()
        else:
            while self.is_busy():
                time.sleep(0.1)
                self.get_position()
            time.sleep(0.1)
        self.get_position()

    def set_zero(self, zero):
        '''
        float zero mm
        '''
        self.zero_position.write(zero)
        min_value = -self.zero_position.read() * ps_per_mm
        max_value = (50. - self.zero_position.read()) * ps_per_mm
        self.limits.write(min_value, max_value, 'ps')
        self.get_position()
        # write new position to ini
        section = 'D{}'.format(self.index)
        option = 'zero position (mm)'
        ini.write(section, option, zero)


### advanced gui ##############################################################


class gui(QtCore.QObject):

    def __init__(self, delay):
        QtCore.QObject.__init__(self)
        self.delay = delay

    def create_frame(self, layout):
        layout.setMargin(5)
        self.layout = layout

        self.advanced_frame = QtGui.QWidget()
        self.advanced_frame.setLayout(self.layout)

        g.module_advanced_widget.add_child(self.advanced_frame)

        if self.delay.initialized.read():
            self.initialize()
        else:
            self.delay.initialized.updated.connect(self.initialize)

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

        # input table
        input_table = pw.InputTable()
        input_table.add('Current', self.delay.current_position_mm)
        input_table.add('Zero', self.delay.zero_position)
        self.zero_destination = self.delay.zero_position.associate(display=False)
        input_table.add('Zero dest.', self.zero_destination)
        settings_layout.addWidget(input_table)

        # set button
        self.set_button = pw.SetButton('SET ZERO')
        settings_layout.addWidget(self.set_button)
        self.set_button.clicked.connect(self.on_set)
        g.module_control.disable_when_true(self.set_button)

        settings_layout.addStretch(1)
        self.layout.addStretch(1)

    def update(self):
        pass

    def on_set(self):
        new_zero = self.zero_destination.read('mm')
        self.delay.set_zero(new_zero)
        self.delay.offset.write(0)
        name = self.delay.address.hardware.name
        g.coset_control.read().zero(name)
    
    def show_advanced(self):
        pass

    def stop(self):
        pass


### testing ###################################################################


if __name__ == '__main__':

    pass
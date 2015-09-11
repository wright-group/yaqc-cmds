### import ####################################################################

import os

import time

from PyQt4 import QtGui, QtCore

import WrightTools.units as wt_units

import project
import project.classes as pc
import project.widgets as pw
import project.project_globals as g

import project.precision_micro_motors.v_precision_motors as pm_motors
from opas.virtual.v_ps_curve_handler import Curve

main_dir = g.main_dir.read()
ini = project.ini_handler.Ini(os.path.join(main_dir, 'opas',
                                                     'pico',
                                                     'pico_opa.ini'))

### Virtual OPA object ########################################################

max_OPA_index = 3

class OPA:

    def __init__(self):
        self.index = 2
        # list of objects to be exposed to PyCMDS
        self.native_units = 'wn'
        # motor positions
        self.motor_limits = pc.NumberLimits(min_value=0, max_value=50)
        self.grating_position = pc.Number(name='Grating', initial_value=25., limits=self.motor_limits, display=True)
        self.bbo_position = pc.Number(name='BBO', initial_value=25., limits=self.motor_limits, display=True)
        self.mixer_position = pc.Number(name='Mixer', initial_value=25., limits=self.motor_limits, display=True)
        self.motor_positions=[self.grating_position, self.bbo_position, self.mixer_position]
        # may wish to have number limits loaded with tuning curve.
        self.limits = pc.NumberLimits(min_value=1200, max_value=19000, units='wn')
        self.current_position = pc.Number(name='Color', initial_value=8000.,
                                          limits=self.limits,
                                          units='wn', display=True,
                                          set_method='set_position')
        self.exposed = [self.current_position]
        self.gui = gui(self)
        self.motors=[]

    def adjust_color(self, old_color, adjust_to):
        OPA.crv.adjust_curve(old_color, adjust_to)

    def close(self):
        for motor in self.motors:
            motor.close()

    def get_curve(self, filepath, polyorder = 4):
        self.polyorder = polyorder
        self.curve = Curve(filepath, self.polyorder)

    def get_position(self):
        m = self.get_motor_positions()
        return self.curve.get_color(m[0], m[1], m[2], self.polyorder)

    def get_motor_positions(self):
        for i in range(len(self.motors)):
            val = self.motors[i].get_position()
            self.motor_positions[i].write(val)
        return [mp.read() for mp in self.motor_positions]

    def initialize(self, inputs, address):
        '''
        OPA initialization method. Inputs = [index]
        '''
        self.address = address
        self.address.update_ui.connect(self.gui.update)
        self.index = inputs[0]
        error = False
        if self.index >= 1 and self.index <= max_OPA_index:
            self.motors.append(pm_motors.Motor(pm_motors.identity['vOPA'+str(self.index)+' grating']))
            self.motors.append(pm_motors.Motor(pm_motors.identity['vOPA'+str(self.index)+' BBO']))
            self.motors.append(pm_motors.Motor(pm_motors.identity['vOPA'+str(self.index)+' mixer']))
            self.curve_path = ini.read('vOPA{}'.format(self.index), 'curve path')
        else:
            error = True
            print('This is not a valid vOPA number in v_pico_OPA.py.')
            g.logger.log('error','vOPA'+str(self.index)+' does not exist.')

        if error:
            print('vOPA'+str(self.index)+' initialization failed')
            g.logger.log('error','vOPA inititailization failed')

        self.get_curve(self.curve_path)
        self.color = self.get_position()

    def is_busy(self):
        for motor in self.motors:
            if not motor.is_stopped():
                return True
        return False

    def is_valid(self, destination):
        '''
        m = self.get_motor_positions()
        if self.limits.read[0]:
            for pos in m:
                if pos >= 0 and pos <=50: # In the To Do: remove raw numbers.
                    pass
                else: return False
        '''
        return True

    def set_curve(self):
        # pick a file
        path = 'OPA tuning curve file path'
        self.get_curve(path)

    def set_position(self, destination, units = 'wn'):
        self.color = self.get_position()
        if units == 'wn':
            if self.is_valid(destination):
                mpos=self.curve.new_motor_positions(destination)
        elif units == 'nm':
            if self.is_valid(10000000/destination):
                mpos = self.curve.new_motor_positions(10000000/destination)
        else:
            print('Units not recognized by pico_opa.py')

            # put in log here too.

        for i in range (0,3):
            self.set_motors(i,mpos[i])

    def set_motors(self, inputs):
        for axis in range(3):
            position = inputs[axis]
            if position >= 0 and position <=50:
                self.motors[axis].move_absolute(position)
            else:
                print('That is not a valid motor positon. Nice try, bucko.')
        self.wait_until_still()
        self.get_motor_positions()

    def wait_until_still(self):
        for motor in self.motors:
            motor.wait_until_still()

### advanced gui ##############################################################


class gui(QtCore.QObject):

    def __init__(self, opa):
        QtCore.QObject.__init__(self)
        self.opa = opa

    def create_frame(self, layout):
        layout.setMargin(5)

        # plot ----------------------------------------------------------------

        # container widget
        display_container_widget = QtGui.QWidget()
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)

        # plot
        self.plot_widget = pw.Plot1D()
        self.plot_curve = self.plot_widget.add_line()
        self.plot_widget.set_labels(ylabel = 'volts')
        self.plot_green_line = self.plot_widget.add_line(color = 'g')
        self.plot_red_line = self.plot_widget.add_line(color = 'r')
        display_layout.addWidget(self.plot_widget)

        # vertical line
        line = pw.line('V')
        layout.addWidget(line)

        # settings container --------------------------------------------------


        # container widget / scroll area
        settings_container_widget = QtGui.QWidget()
        settings_scroll_area = pw.scroll_area()
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        layout.addWidget(settings_scroll_area)

        # Display
        input_table = pw.InputTable()
        input_table.add('Display', None)
        settings_layout.addWidget(input_table)

        # horizontal line
        line = pw.line('H')
        settings_layout.addWidget(line)

        # Tuning Curve
        input_table = pw.InputTable()
        input_table.add('Curve', None)
        settings_layout.addWidget(input_table)

        # horizontal line
        line = pw.line('H')
        settings_layout.addWidget(line)

        # Motor Positions
        input_table = pw.InputTable()
        input_table.add('Motors', None)
        input_table.add('Grating', self.opa.grating_position)
        self.grating_destination = self.opa.grating_position.associate(display=False)
        input_table.add('Dest. Grating', self.grating_destination)
        input_table.add('BBO', self.opa.bbo_position)
        self.bbo_destination = self.opa.bbo_position.associate(display=False)
        input_table.add('Dest. BBO', self.bbo_destination)
        input_table.add('Mixer', self.opa.mixer_position)
        self.mixer_destination = self.opa.mixer_position.associate(display=False)
        input_table.add('Dest. Mixer', self.mixer_destination)
        settings_layout.addWidget(input_table)
        self.destinations = [self.grating_destination,
                             self.bbo_destination,
                             self.mixer_destination]

        # set button
        self.set_button = pw.SetButton('SET')
        settings_layout.addWidget(self.set_button)
        self.set_button.clicked.connect(self.on_set_motors)
        g.module_control.disable_when_true(self.set_button)

        # streach
        settings_layout.addStretch(1)

        # add -----------------------------------------------------------------

        self.advanced_frame = QtGui.QWidget()
        self.advanced_frame.setLayout(layout)

        g.module_advanced_widget.add_child(self.advanced_frame)

    def update(self):
        if self.opa.address.busy.read():
            self.set_button.setDisabled(True)
        else:
            self.set_button.setDisabled(False)

    def on_set_motors(self):
        inputs = [destination.read() for destination in self.destinations]
        self.opa.address.hardware.q.push('set_motors', inputs)

    def show_advanced(self):
        pass

    def stop(self):
        pass


### testing ###################################################################


if __name__ == '__main__':
    pass

### import ####################################################################

import os
import collections
import time

import numpy as np

from PyQt4 import QtGui, QtCore

import WrightTools as wt
import WrightTools.units as wt_units

import project
import project.classes as pc
import project.widgets as pw
import project.project_globals as g

if g.offline.read():
    import project.precision_micro_motors.v_precision_motors as pm_motors
else:
    import project.precision_micro_motors.precision_motors as pm_motors

main_dir = g.main_dir.read()
ini = project.ini_handler.Ini(os.path.join(main_dir, 'opas',
                                                     'pico',
                                                     'pico_opa.ini'))


### curve object ##############################################################


class Curve:

    def __init__(self, filepath, n = 4):
        '''
        filepath string \npoints
        n integer degree of polynomial fit
        '''
        self.filepath = filepath

        self.points = np.genfromtxt(filepath).T

        self.min = self.points[0].min()
        self.max = self.points[0].max()
        self.num = len(self.points[0])

        # fit motor polynomials -----------------------------------------------

        m0 = np.polynomial.polynomial.polyfit(self.points[0], self.points[1], n, full=True)
        m1 = np.polynomial.polynomial.polyfit(self.points[0], self.points[2], n, full=True)
        m2 = np.polynomial.polynomial.polyfit(self.points[0], self.points[3], n, full=True)
        self.motor_functions = [m0, m1, m2]

    def get_motor_positions(self, color):
        '''
        color in wn \n
        returns list [m0, m1, m2], mm
        '''
        return [np.polynomial.polynomial.polyval(color, self.motor_functions[i][0]) for i in range(3)]

    def get_color(self, m0, m1, m2):
        '''
        returns color from motor positions
        '''
        # Modify stored function by subtracting motor position, find roots ----

        a1 = self.motor_functions[0][0][::-1].copy()
        a2 = self.motor_functions[1][0][::-1].copy()
        a3 = self.motor_functions[2][0][::-1].copy()

        a1[4] -= m0
        a2[4] -= m1
        a3[4] -= m2

        color_a1 = np.real(np.roots(a1)[3])
        color_a2 = np.real(np.roots(a2)[3])
        color_a3 = np.real(np.roots(a3)[3])

        # Round the color values to make them equal ---------------------------

        d = 0
        color = [0, 0, 0]
        color[0] = np.around(color_a1, decimals=d)
        color[1] = np.around(color_a2, decimals=d)
        color[2] = np.around(color_a3, decimals=d)

        # only return color if all motors signify same wavenumber -------------

        if color[0] == color[1] and color [0] == color[2]:
            return color[0]
        else:
            return np.nan


def save_curve(points, old_curve_filepath):
    directory, name, extension = wt.kit.filename_parse(old_curve_filepath)
    if g.offline:
        new_name = 'v_' + name.split(' - ')[0] + ' - ' + wt.kit.get_timestamp() + '.curve'
    else:
        new_name = name.split(' - ')[0] + ' - ' + wt.kit.get_timestamp() + '.curve'
    output_path = os.path.join(directory, new_name)
    header = 'color (wn)\tGrating\tBBO\tMixer'
    np.savetxt(output_path, points.T, fmt='%0.2f', delimiter='\t', header=header)


### OPA object ################################################################


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
        self.limits = pc.NumberLimits(min_value=6200, max_value=9500, units='wn')
        self.current_position = pc.Number(name='Color', initial_value=2000.,
                                          limits=self.limits,
                                          units='wn', display=True,
                                          set_method='set_position')
        self.exposed = [self.current_position]
        self.recorded = collections.OrderedDict()
        self.gui = gui(self)
        self.motors=[]
        self.motor_names = ['Grating', 'BBO', 'Mixer']
        self.initialized = pc.Bool()

    def close(self):
        for motor in self.motors:
            motor.close()

    def load_curve(self, filepath, polyorder = 4):
        self.polyorder = polyorder
        self.curve = Curve(filepath, self.polyorder)
        self.limits.write(self.curve.min, self.curve.max, 'wn')

    def get_points(self):
        return self.curve.points

    def get_position(self):
        m = self.get_motor_positions()
        color = self.curve.get_color(m[0], m[1], m[2])
        self.current_position.write(color, self.native_units)
        return color

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
        self.index = inputs[0]
        # load motors
        self.motors.append(pm_motors.Motor(pm_motors.identity['OPA'+str(self.index)+' grating']))
        self.motors.append(pm_motors.Motor(pm_motors.identity['OPA'+str(self.index)+' BBO']))
        self.motors.append(pm_motors.Motor(pm_motors.identity['OPA'+str(self.index)+' mixer']))
        self.get_motor_positions()
        # load curve
        self.curve_path = pc.Filepath(ini=ini, section='OPA%d'%self.index, option='curve path', import_from_ini=True, save_to_ini_at_shutdown=True, options=['Curve File (*.curve)'])
        self.curve_path.updated.connect(self.curve_path.save)
        self.curve_path.updated.connect(lambda: self.load_curve(self.curve_path.read()))
        self.load_curve(self.curve_path.read())
        self.get_position()
        # define values to be recorded by DAQ
        self.recorded['w%d'%self.index] = [self.current_position, 'wn', 1., str(self.index), False]
        self.recorded['w%d_grating'%self.index] = [self.grating_position, None, 0.1, 'grating', True]
        self.recorded['w%d_bbo'%self.index] = [self.bbo_position, None, 0.1, 'bbo', True]
        self.recorded['w%d_mixer'%self.index] = [self.mixer_position, None, 0.1, 'mixer', True]
        self.initialized.write(True)

    def is_busy(self):
        for motor in self.motors:
            if not motor.is_stopped():
                return True
        return False

    def is_valid(self, destination):
        return True

    def set_position(self, destination):
        motor_destinations = self.curve.get_motor_positions(destination)
        self.set_motors(motor_destinations)
        self.get_position()

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
        self.layout = None

    def create_frame(self, layout):
        layout.setMargin(5)
        self.layout = layout

        self.advanced_frame = QtGui.QWidget()
        self.advanced_frame.setLayout(self.layout)

        g.module_advanced_widget.add_child(self.advanced_frame)

        if self.opa.initialized.read():
            self.initialize()
        else:
            self.opa.initialized.updated.connect(self.initialize)

    def initialize(self):

        if not self.opa.initialized.read():
            return

        # plot ----------------------------------------------------------------

        # container widget
        display_container_widget = QtGui.QWidget()
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        self.layout.addWidget(display_container_widget)

        # plot
        self.plot_widget = pw.Plot1D()
        self.plot_widget.plot_object.setMouseEnabled(False, False)
        self.plot_curve = self.plot_widget.add_scatter()
        self.plot_widget.set_labels(ylabel = 'mm')
        self.plot_green_line = self.plot_widget.add_line(color = 'g')
        self.plot_red_line = self.plot_widget.add_line(color = 'r')
        display_layout.addWidget(self.plot_widget)

        # vertical line
        line = pw.line('V')
        self.layout.addWidget(line)

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
        self.layout.addWidget(settings_scroll_area)

        # Display
        input_table = pw.InputTable()
        input_table.add('Display', None)
        allowed_values = wt_units.energy.keys()
        allowed_values.remove('kind')
        self.plot_motor = pc.Combo(allowed_values=self.opa.motor_names)
        input_table.add('Motor', self.plot_motor)
        self.plot_units = pc.Combo(allowed_values=allowed_values)
        input_table.add('Units', self.plot_units)
        settings_layout.addWidget(input_table)

        # Tuning Curve
        input_table = pw.InputTable()
        input_table.add('Curve', None)
        input_table.add('Filepath', self.opa.curve_path)
        self.lower_limit = pc.Number(initial_value=7000, units=self.opa.native_units, display=True)
        input_table.add('Low energy limit', self.lower_limit)
        self.upper_limit = pc.Number(initial_value=7000, units=self.opa.native_units, display=True)
        input_table.add('High energy limit', self.upper_limit)
        settings_layout.addWidget(input_table)

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

        # signals and slots
        self.opa.address.update_ui.connect(self.update)
        self.opa.limits.updated.connect(self.update_limits)
        self.update_limits()  # first time
        self.opa.curve_path.updated.connect(self.update_plot)
        self.plot_units.updated.connect(self.update_plot)
        self.plot_motor.updated.connect(self.update_plot)
        self.update_plot()  # first time

    def update(self):
        # set button disable
        if self.opa.address.busy.read():
            self.set_button.setDisabled(True)
        else:
            self.set_button.setDisabled(False)
        # update destination motor positions
        motor_positions = [mp.read() for mp in self.opa.motor_positions]
        self.grating_destination.write(motor_positions[0])
        self.bbo_destination.write(motor_positions[1])
        self.mixer_destination.write(motor_positions[2])

    def update_plot(self):
        points = self.opa.get_points()
        xi = wt_units.converter(points[0], 'wn', self.plot_units.read())
        motor_index = self.opa.motor_names.index(self.plot_motor.read())+1
        yi = points[motor_index]
        self.plot_widget.set_labels(xlabel=self.plot_units.read())
        self.plot_curve.clear()
        self.plot_curve.setData(xi, yi)
        self.plot_widget.graphics_layout.update()

    def update_limits(self):
        limits = self.opa.limits.read(self.opa.native_units)
        self.lower_limit.write(limits[0], self.opa.native_units)
        self.upper_limit.write(limits[1], self.opa.native_units)

    def on_set_motors(self):
        inputs = [destination.read() for destination in self.destinations]
        self.opa.address.hardware.q.push('set_motors', inputs)
        self.opa.get_position()

    def show_advanced(self):
        pass

    def stop(self):
        pass


### testing ###################################################################


if __name__ == '__main__':
    pass

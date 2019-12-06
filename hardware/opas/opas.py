### import ####################################################################


import os
import time
import shutil
import collections

import numpy as np

from PySide2 import QtWidgets

import WrightTools as wt
import attune

import project.project_globals as g
import project.widgets as pw
import project.ini_handler as ini
import project.classes as pc
import hardware.hardware as hw
from hardware.opas.PoyntingCorrection.ZaberCorrectionDevice import ZaberCorrectionDevice


### define ####################################################################


directory = os.path.dirname(os.path.abspath(__file__))

main_dir = g.main_dir.read()
app = g.app.read()
ini = ini.opas


### driver ####################################################################


class Driver(hw.Driver):

    def __init__(self, *args, **kwargs):
        self.hardware_ini = ini
        self.index = kwargs['index']
        self.motor_positions = collections.OrderedDict()
        self.homeable = {}  # TODO:
        self.poynting_type = kwargs.pop('poynting_type')
        self.poynting_correction  = None
        self.poynting_curve_path = kwargs.pop('poynting_curve_path')
        hw.Driver.__init__(self, *args, **kwargs)
        if not hasattr(self, 'motor_names'):  # for virtual...
            self.motor_names = ['Delay', 'Crystal', 'Mixer']
        if not hasattr(self, 'curve_paths'):  # for virtual...
            self.curve_paths = collections.OrderedDict()
        if not hasattr(self, 'interaction_string_combo'):  # for virtual...
            self.interaction_string_combo = pc.Combo(allowed_values=['sig'])
        if self.poynting_type is not None:
            self.motor_names += ['Phi', 'Theta'] #TODO: Generalize
        self.curve = None
        # poynting correction
        if self.poynting_type == 'zaber':
            self.poynting_correction = ZaberCorrectionDevice(kwargs.pop('poynting_port'), kwargs.pop('poynting_indexes'))
        else:
            self.poynting_correction = None
            self.poynting_type = None

        if self.poynting_correction:
           self.curve_paths['Poynting'] = pc.Filepath(initial_value=self.poynting_curve_path)
        if self.model == 'Virtual':
            self.load_curve()

    def _home_motors(self, motor_names):
        raise NotImplementedError

    def _load_curve(self, interaction):
        if self.model == 'Virtual':
            colors = np.linspace(400, 10000, 17)
            motors = []
            motors.append(attune.Dependent(((colors-500)/1e4)**2, 'Delay'))
            motors.append(attune.Dependent(-(colors-90)**0.25, 'Crystal'))
            motors.append(attune.Dependent((colors-30)**0.25, 'Mixer'))
            name = 'curve'
            interaction = 'sig'
            kind = 'Virtual'
            colors = attune.Setpoints(colors, "Colors", units="nm")
            self.curve = attune.Curve(colors, motors, name, interaction, kind)
            self.curve.convert(self.native_units)
        else:
            raise NotImplementedError

    def _set_motors(self, motor_destinations):
        if self.model == 'Virtual':
            #Virtual hardware, just set the position directly
            for k, v in motor_destinations.items():
                self.motor_positions[k].write(v)
        else:
            raise NotImplementedError

    def _update_api(self, interaction):
        pass

    def _wait_until_still(self, inputs=[]):
        while self.is_busy():
            print("waiting", self.hardware.name)
            time.sleep(0.1)  # I've experienced hard crashes when wait set to 0.01 - Blaise 2015.12.30
            self.get_motor_positions()
        self.get_motor_positions()

    def get_position(self):
        position = self.hardware.destination.read()
        self.position.write(position, self.native_units)
        return position
        
    def get_motor_positions(self):
        pass

    def home_all(self, inputs=[]):
        names = [i for i in self.motor_names if self.homeable.get(i) ]
        if self.poynting_correction:
            self.poynting_correction.home()
            for n in self.poynting_correction.motor_names:
                names.pop(n, None)
        self._home_motors(names)

    def home_motor(self, inputs):
        # TODO: clean up for new inputs behavior
        motor_name = inputs[0]
        if self.poynting_correction:
            if motor_name in self.poynting_correction.motor_names:
                self.poynting_correction.home(motor_name)
                return
        if self.homeable.get(motor_name):
            self._home_motors([motor_name])

    def initialize(self):
        # virtual stuff
        if self.model == 'Virtual':
            self.motor_positions['Delay'] = pc.Number(0., display=True)
            self.motor_positions['Crystal'] = pc.Number(0., display=True)
            self.motor_positions['Mixer'] = pc.Number(0., display=True)
        if self.poynting_correction:
             # initialize
            self.poynting_correction.initialize(self)  
            for name in self.poynting_correction.motor_names:
                self.homeable[name] = True
                number = self.poynting_correction.motor_positions[name]
                self.motor_positions[name] = number
                self.recorded[self.name + '_' + name] = [number, None, 1., name]
        # get position
        self.load_curve()
        self.get_motor_positions()
        self.get_position()
        hw.Driver.initialize(self)

    def load_curve(self, name=None, path=None, update=True):
        interaction = self.interaction_string_combo.read()
        # update curve_paths
        if name is not None:
            old_directory = os.path.dirname(str(self.curve_paths[name]))
            p = shutil.copy(path, old_directory)
            self.curve_paths[name].write(os.path.abspath(p))
        # remake own curve object
        curve = self._load_curve(interaction)
        if self.poynting_correction:
            p = self.curve_paths['Poynting'].read()
            self.curve = attune.Curve.read(p, subcurve=curve)
            self.curve.kind = "poynting"
            self.hardware_ini.write(self.name, 'poynting_curve_path', p)
        self.curve.convert(self.native_units)
        # update limits
        self.limits.write(*self.curve.get_limits(), self.native_units)
        if update:
            self._update_api(interaction)


    def set_motor(self, motor_name, destination, wait=True):
        
        if self.poynting_correction:
            if motor_name in self.poynting_correction.motor_names:
                self.poynting_correction.set_motor(motor_name, destination)
                return
        self._set_motors({motor_name: destination})
        if wait:
            self.wait_until_still()

    def set_motors(self, motor_names, motor_positions, wait=True):
        destinations = {n: p for n,p in zip(motor_names, motor_positions)}
        if self.poynting_correction:
            for name, pos in zip(motor_names, motor_positions):
                if name in self.poynting_correction.motor_names:
                    self.poynting_correction.set_motor(name, pos)
                    destinations.pop(name)
        self._set_motors(destinations)
        if wait:
            self.wait_until_still()

    def set_position(self, destination):
        # coerce destination to be within current tune range
        destination = np.clip(destination, *self.curve.get_limits())
        # get destinations from curve
        motor_destinations = self.curve(destination, self.native_units)
        # poynting
        if self.poynting_correction:
            for m in self.poynting_correction.motor_names:
                self.poynting_correction.set_motor(m, motor_destinations.pop(m))
        # OPA
        self._set_motors(motor_destinations)
        time.sleep(0.01)
        # finish
        self.wait_until_still()
        self.get_position()
        
    def set_position_except(self, destination, exceptions):
        '''
        set position, except for motors that follow
        
        does not wait until still...
        '''
        self.hardware.destination.write(destination, self.native_units)
        self.position.write(destination, self.native_units)
        motor_destinations = self.curve(destination, self.native_units)
        for e in exceptions:
            motor_destinations.pop(e, None)
        if self.poynting_correction:
            for m in self.poynting_correction.motor_names:
                if m in motor_destinations:
                    self.poynting_correction.set_motor(m, motor_destinations.pop(m))
        self._set_motors(motor_destinations)

    def wait_until_still(self):
        self._wait_until_still()
        if self.poynting_correction:
            self.poynting_correction.wait_until_still()
        self.get_motor_positions()


### gui #######################################################################


class GUI(hw.GUI):

    def initialize(self):
        #self.hardware.driver.initialize()
        # container widget
        display_container_widget = QtWidgets.QWidget()
        display_container_widget.setLayout(QtWidgets.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        self.layout.addWidget(display_container_widget)
        # plot
        self.plot_widget = pw.Plot1D()
        self.plot_widget.plot_object.setMouseEnabled(False, False)
        self.plot_curve = self.plot_widget.add_scatter()
        self.plot_h_line = self.plot_widget.add_infinite_line(angle=0, hide=False)
        self.plot_v_line = self.plot_widget.add_infinite_line(angle=90, hide=False)
        display_layout.addWidget(self.plot_widget)
        # vertical line
        line = pw.line('V')
        self.layout.addWidget(line)
        # container widget / scroll area
        settings_container_widget = QtWidgets.QWidget()
        settings_scroll_area = pw.scroll_area()
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtWidgets.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        self.layout.addWidget(settings_scroll_area)
        # opa properties
        input_table = pw.InputTable()
        settings_layout.addWidget(input_table)
        # plot control
        input_table = pw.InputTable()
        input_table.add('Display', None)
        self.plot_motor = pc.Combo(allowed_values=self.driver.curve.dependent_names)
        self.plot_motor.updated.connect(self.update_plot)
        input_table.add('Motor', self.plot_motor)
        allowed_values = list(wt.units.energy.keys())
        self.plot_units = pc.Combo(initial_value=self.driver.native_units, allowed_values=allowed_values)
        self.plot_units.updated.connect(self.update_plot)
        input_table.add('Units', self.plot_units)
        settings_layout.addWidget(input_table)
        # curves
        input_table = pw.InputTable()
        input_table.add('Curves', None)
        for name, obj in self.driver.curve_paths.items():
            input_table.add(name, obj)
            obj.updated.connect(self.on_curve_paths_updated)
        input_table.add('Interaction String', self.driver.interaction_string_combo)
        # limits
        limits = pc.NumberLimits()  # units None
        self.low_energy_limit_display = pc.Number(units=self.driver.native_units, display=True, limits=limits)
        input_table.add('Low Energy Limit', self.low_energy_limit_display)
        self.high_energy_limit_display = pc.Number(units=self.driver.native_units, display=True, limits=limits)
        input_table.add('High Energy LImit', self.high_energy_limit_display)
        settings_layout.addWidget(input_table)
        self.driver.limits.updated.connect(self.on_limits_updated)
        # motors
        input_table = pw.InputTable()
        input_table.add('Motors', None)
        settings_layout.addWidget(input_table)
        for motor_name, motor_mutex in self.driver.motor_positions.items():
            settings_layout.addWidget(MotorControlGUI(motor_name, motor_mutex, self.driver))
        self.home_all_button = pw.SetButton('HOME ALL', 'advanced')
        settings_layout.addWidget(self.home_all_button)
        homeable = any(self.driver.homeable)
        self.home_all_button.clicked.connect(self.on_home_all)
        g.queue_control.disable_when_true(self.home_all_button)
        # poynting manual mode
        if self.driver.poynting_correction:
            self.poynting_manual_control = pc.Bool()
            input_table = pw.InputTable()
            input_table.add('Poynting Control', self.poynting_manual_control)
            self.poynting_manual_control.updated.connect(self.on_poynting_manual_control_updated)
            settings_layout.addWidget(input_table)
        # stretch
        settings_layout.addStretch(1)
        # signals and slots
        self.driver.interaction_string_combo.updated.connect(self.update_plot)
        self.driver.update_ui.connect(self.update)
        # finish
        self.update()
        self.update_plot()
        self.on_limits_updated()

    def update(self):
        # set button disable
        if self.driver.busy.read():
            self.home_all_button.setDisabled(True)
            for motor_mutex in self.driver.motor_positions.values():
                motor_mutex.set_disabled(True)
        else:
            self.home_all_button.setDisabled(False)
            for motor_mutex in self.driver.motor_positions.values():
                motor_mutex.set_disabled(False)
        # update destination motor positions
        # TODO: 
        # update plot lines
        motor_name = self.plot_motor.read()
        motor_position = self.driver.motor_positions[motor_name].read()
        self.plot_h_line.setValue(motor_position)
        units = self.plot_units.read()
        self.plot_v_line.setValue(self.driver.position.read(units))

    def update_plot(self):
        # units
        units = self.plot_units.read()
        # xi
        colors = self.driver.curve.setpoints[:]
        xi = wt.units.converter(colors, self.driver.curve.setpoints.units, units)
        # yi
        self.plot_motor.set_allowed_values(self.driver.curve.dependent_names)  # can be done on initialization?
        motor_name = self.plot_motor.read()
        yi = self.driver.curve(xi, units)[motor_name]
        self.plot_widget.set_labels(xlabel=units, ylabel=motor_name)
        self.plot_curve.clear()
        try:
            self.plot_curve.setData(xi, yi)
        except ValueError:
            pass
        self.plot_widget.graphics_layout.update()
        self.update()
        self.plot_motor.set_allowed_values(self.driver.curve.dependent_names)

    def on_curve_paths_updated(self):
        self.driver.load_curve()  # TODO: better
        self.update_plot()

    def on_home_all(self):
        self.hardware.q.push('home_all')
        
    def on_limits_updated(self):
        low_energy_limit, high_energy_limit = self.driver.limits.read('wn')
        self.low_energy_limit_display.write(low_energy_limit, 'wn')
        self.high_energy_limit_display.write(high_energy_limit, 'wn')
        
    def on_poynting_manual_control_updated(self):
        if self.poynting_manual_control.read():
            self.driver.poynting_correction.port.setMode('manual')
        else:
            self.driver.poynting_correction.port.setMode('computer')


class MotorControlGUI(QtWidgets.QWidget):
    
    def __init__(self, motor_name, motor_mutex, driver):
        QtWidgets.QWidget.__init__(self)
        self.motor_name = motor_name
        self.driver = driver
        self.hardware = driver.hardware
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setMargin(0)
        # table
        input_table = pw.InputTable()
        input_table.add(motor_name, motor_mutex)
        self.destination = motor_mutex.associate(display=False)
        input_table.add('Dest. ' + motor_name, self.destination)
        self.layout.addWidget(input_table)
        # buttons
        home_button, set_button = self.add_buttons(self.layout, 'HOME', 'advanced', 'SET', 'set')
        home_button.clicked.connect(self.on_home)
        set_button.clicked.connect(self.on_set)
        g.queue_control.disable_when_true(home_button)
        g.queue_control.disable_when_true(set_button)
        # finish
        self.setLayout(self.layout)
            
    def add_buttons(self, layout, button1_text, button1_color, button2_text, button2_color):
        colors = g.colors_dict.read()
        # layout
        button_container = QtWidgets.QWidget()
        button_container.setLayout(QtWidgets.QHBoxLayout())
        button_container.layout().setMargin(0)
        # button1
        button1 = QtWidgets.QPushButton()
        button1.setText(button1_text)
        button1.setMinimumHeight(25)
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors[button1_color])
        button1.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(button1)
        g.queue_control.disable_when_true(button1)
        # button2
        button2 = QtWidgets.QPushButton()
        button2.setText(button2_text)
        button2.setMinimumHeight(25)
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors[button2_color])
        button2.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(button2)
        g.queue_control.disable_when_true(button2)
        # finish
        layout.addWidget(button_container)
        return [button1, button2]
        
    def on_home(self):
        self.driver.hardware.q.push('home_motor', [self.motor_name])
    
    def on_set(self):
        destination = self.destination.read()
        self.hardware.set_motor(self.motor_name, destination)


### hardware ##################################################################


class Hardware(hw.Hardware):
    
    def __init__(self, *arks, **kwargs):
        self.kind = 'OPA'
        hw.Hardware.__init__(self, *arks, **kwargs)

    @property
    def curve(self):
        # TODO: a more thread-safe operation (copy?)
        return self.driver.curve
    
    @property
    def curve_paths(self):
        """
        OrderedDict {name: path}
        """
        # TODO: a more thread-safe operation
        return collections.OrderedDict({key: value.read() for key, value in self.driver.curve_paths.items()})

    def get_tune_points(self, units='native'):
        if units == 'native':
            units = self.native_units
        return wt.units.converter(self.curve.setpoints[:], self.curve.setpoints.units, units)

    def home_motor(self, motor):
        """
        motor list [name]
        """
        self.q.push('home_motor', motor)

    def load_curve(self, name, path):
        self.q.push('load_curve', name, path)

    @property
    def motor_names(self):
        # TODO: a more thread-safe operation
        return self.driver.motor_names
        
    def set_motor(self, motor, destination):
        self.q.push('set_motor', motor, destination)


### initialize ################################################################


ini_path = os.path.join(directory, 'opas.ini')
hardwares, gui, advanced_gui = hw.import_hardwares(ini_path, name='OPAs', Driver=Driver, GUI=GUI, Hardware=Hardware)

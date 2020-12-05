## import ####################################################################


import time
import pathlib

import appdirs
import toml

from PySide2 import QtWidgets

import WrightTools as wt
import attune
import yaqc

import yaqc_cmds.__main__
import yaqc_cmds.project.project_globals as g
import yaqc_cmds.project.widgets as pw
import yaqc_cmds.project.classes as pc
from yaqc_cmds.hardware import hardware as hw
from yaqc_cmds.somatic import signals


### driver ####################################################################


class Driver(hw.Driver):
    def __init__(self, *args, **kwargs):
        self.yaqd_port = kwargs["yaqd_port"]
        self.yaqd_host = kwargs.get("yaqd_host", "127.0.0.1")
        self.client = yaqc.Client(self.yaqd_port, host=self.yaqd_host)
        self.client.register_connection_callback(signals.updated_attune_store.emit)
        signals.updated_attune_store.connect(self.on_updated_attune_store)
        self.motor_positions = {
            k: pc.Number(name=k, decimals=6, display=True) for k in self.client.get_setable_names()
        }
        hw.Driver.__init__(self, *args, **kwargs)
        self.shutter_port = kwargs.get("shutter_yaqd_port")
        if self.shutter_port:
            self.shutter_position = pc.Bool(name="Shutter", display=True, set_method="set_shutter")
            self.shutter = yaqc.Client(self.shutter_port)
            self.shutter.set_identifier("closed")
            self.exposed += [self.shutter_position]
        self.on_updated_attune_store()

    def on_updated_attune_store(self):
        self.curve = attune.Instrument(**self.client.get_instrument())
        self.load_curve()
        self.get_motor_positions()
        self.get_position()

    def is_busy(self):
        return self.client.busy()

    def get_position(self):
        position = self.client.get_position()
        self.position.write(position, self.native_units)
        return position

    def get_motor_positions(self):
        positions = self.client.get_setable_positions()
        for k, v in self.motor_positions.items():
            v.write(positions[k])

    def home_all(self, inputs=None):
        if self.shutter_port:
            self.set_shutter([0])
        self.client.home()

    def home_motor(self, inputs):
        if self.shutter_port:
            self.set_shutter([0])
        self.client.home_setables([inputs])

    def load_curve(self, path=None):
        self.recorded[self.name] = [
            self.position,
            self.native_units,
            None,
            self.label.read(),
            None,
        ]
        for name, sa in self.motor_positions.items():
            self.recorded[f"{self.name}_{name}"] = [sa, None, None, name.lower(), None]
        self.set_arrangement(self.arrangement)

    def set_motor(self, motor_name, destination, wait=True):
        self.client.set_setable_positions({motor_name: destination})
        if wait:
            self.wait_until_still()

    def set_motors(self, motor_names, motor_positions, wait=True):
        destinations = {n: p for n, p in zip(motor_names, motor_positions)}
        self.client.set_setable_positions(destinations)
        if wait:
            self.wait_until_still()

    def set_position(self, destination, units=None):
        if units:
            destination = wt.units.convert(destination, units, self.native_units)
        self.client.set_position(destination)
        self.wait_until_still()
        self.get_position()
        self.save_status()

    def set_position_except(self, destination, exceptions, units=None):
        """
        set position, except for motors that follow

        does not wait until still...
        """
        if units:
            destination = wt.units.convert(destination, units, self.native_units)
        self.hardware.destination.write(destination, self.native_units)
        self.position.write(destination, self.native_units)
        self.client.set_position_except(destination, exceptions)
        self.get_position()
        self.save_status()

    def wait_until_still(self):
        while self.is_busy():
            time.sleep(0.01)
            self.get_motor_positions()
            self.get_position()
        self.get_motor_positions()
        self.get_position()

    def set_arrangement(self, arrangement):
        self.client.set_arrangement(arrangement)
        self.limits.write(*self.client.get_limits(), self.native_units)

    @property
    def arrangement(self):
        return self.client.get_arrangement()

    def get_all_arrangements(self):
        return self.client.get_all_arrangements()

    def set_shutter(self, inputs):
        shutter_state = inputs[0]
        error = self.shutter.set_position(shutter_state)
        self.shutter_position.write(shutter_state)
        return error

    def close(self):
        if self.shutter_port:
            self.set_shutter([0])


### gui #######################################################################


class GUI(hw.GUI):
    def initialize(self):
        arr = self.driver.arrangement
        # self.hardware.driver.initialize()
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
        line = pw.line("V")
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
        input_table.add("Display", None)
        self.plot_motor = pc.Combo(allowed_values=self.driver.curve.arrangements[arr].keys())
        self.plot_motor.updated.connect(self.update_plot)
        input_table.add("Motor", self.plot_motor)
        allowed_values = list(wt.units.energy.keys())
        self.plot_units = pc.Combo(
            initial_value=self.driver.native_units, allowed_values=allowed_values
        )
        self.plot_units.updated.connect(self.update_plot)
        input_table.add("Units", self.plot_units)
        settings_layout.addWidget(input_table)
        # curves
        input_table = pw.InputTable()
        # input_table.add("Curves", None)
        self.arrangement_combo = pc.Combo(allowed_values=self.driver.curve.arrangements.keys())
        self.arrangement_combo.write(arr)
        self.arrangement_combo.updated.connect(self.on_arrangement_updated)
        input_table.add("Arrangement", self.arrangement_combo)
        # limits
        limits = pc.NumberLimits()  # units None
        self.low_energy_limit_display = pc.Number(
            units=self.driver.native_units, display=True, limits=limits
        )
        input_table.add("Low Energy Limit", self.low_energy_limit_display)
        self.high_energy_limit_display = pc.Number(
            units=self.driver.native_units, display=True, limits=limits
        )
        input_table.add("High Energy Limit", self.high_energy_limit_display)
        settings_layout.addWidget(input_table)
        self.driver.limits.updated.connect(self.on_limits_updated)
        # motors
        input_table = pw.InputTable()
        input_table.add("Setable", None)
        settings_layout.addWidget(input_table)
        for motor_name, motor_mutex in self.driver.motor_positions.items():
            settings_layout.addWidget(MotorControlGUI(motor_name, motor_mutex, self.driver))
        self.home_all_button = pw.SetButton("HOME ALL", "advanced")
        settings_layout.addWidget(self.home_all_button)
        self.home_all_button.clicked.connect(self.on_home_all)
        g.queue_control.disable_when_true(self.home_all_button)
        # stretch
        settings_layout.addStretch(1)
        # signals and slots
        self.arrangement_combo.updated.connect(self.update_plot)
        self.driver.update_ui.connect(self.update)
        # finish
        self.update()
        self.update_plot()
        self.on_limits_updated()
        signals.updated_attune_store.connect(self.update_plot)

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
        try:
            motor_position = self.driver.motor_positions[motor_name].read()
            self.plot_h_line.setValue(motor_position)
        except:
            pass
        units = self.plot_units.read()
        self.plot_v_line.setValue(self.driver.position.read(units))

    def update_plot(self):
        arr = self.arrangement_combo.read()
        motor_name = self.plot_motor.read()
        tune = self.driver.curve.arrangements[arr][motor_name]
        # units
        units = self.plot_units.read()
        # xi
        colors = tune.independent
        xi = wt.units.converter(colors, tune.ind_units, units)
        # yi
        yi = tune.dependent
        self.plot_widget.set_labels(xlabel=units, ylabel=motor_name)
        self.plot_curve.clear()
        try:
            self.plot_curve.setData(xi, yi)
        except ValueError:
            pass
        self.plot_widget.graphics_layout.update()
        self.update()

    def on_curve_paths_updated(self):
        self.driver.load_curve()  # TODO: better
        self.update_plot()

    def on_home_all(self):
        self.hardware.q.push("home_all")

    def on_limits_updated(self):
        low_energy_limit, high_energy_limit = self.driver.limits.read("wn")
        self.low_energy_limit_display.write(low_energy_limit, "wn")
        self.high_energy_limit_display.write(high_energy_limit, "wn")

    def on_arrangement_updated(self):
        arr = self.arrangement_combo.read()
        self.driver.set_arrangement(arr)
        self.plot_motor.set_allowed_values(self.driver.curve.arrangements[arr].keys())
        self.update_plot()


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
        input_table.add("Dest. " + motor_name, self.destination)
        self.layout.addWidget(input_table)
        # buttons
        home_button, set_button = self.add_buttons(self.layout, "HOME", "advanced", "SET", "set")
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
        StyleSheet = "QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}".replace(
            "custom_color", colors[button1_color]
        )
        button1.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(button1)
        g.queue_control.disable_when_true(button1)
        # button2
        button2 = QtWidgets.QPushButton()
        button2.setText(button2_text)
        button2.setMinimumHeight(25)
        StyleSheet = "QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}".replace(
            "custom_color", colors[button2_color]
        )
        button2.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(button2)
        g.queue_control.disable_when_true(button2)
        # finish
        layout.addWidget(button_container)
        return [button1, button2]

    def on_home(self):
        self.hardware.home_motor(self.motor_name)

    def on_set(self):
        destination = self.destination.read()
        self.hardware.set_motor(self.motor_name, destination)


### hardware ##################################################################


class Hardware(hw.Hardware):
    def __init__(self, *arks, **kwargs):
        self.kind = "OPA"
        hw.Hardware.__init__(self, *arks, **kwargs)

    @property
    def curve(self):
        return self.driver.curve

    def home_motor(self, motor):
        self.q.push("home_motor", motor)

    def load_curve(self, name, path):
        self.q.push("load_curve", name, path)

    @property
    def motor_names(self):
        return list(self.driver.motor_positions.keys())

    def set_motor(self, motor, destination):
        self.q.push("set_motor", motor, destination)

    @property
    def arrangement(self):
        return self.driver.arrangement


### initialize ################################################################


conf = yaqc_cmds.__main__.config
hardwares, gui, advanced_gui = hw.import_hardwares(
    conf.get("hardware", {}).get("opas", {}),
    name="OPAs",
    Driver=Driver,
    GUI=GUI,
    Hardware=Hardware,
)

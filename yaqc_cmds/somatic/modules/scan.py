### import ####################################################################

import pathlib
import time

import numpy as np

import matplotlib

matplotlib.pyplot.ioff()

from PySide2 import QtWidgets
import WrightTools as wt

import yaqc_cmds.project.project_globals as g
import yaqc_cmds.project.classes as pc
import yaqc_cmds.project.widgets as pw
import yaqc_cmds.somatic.acquisition as acquisition

import yaqc_cmds
import yaqc_cmds.hardware.spectrometers as spectrometers
import yaqc_cmds.hardware.delays as delays
import yaqc_cmds.hardware.opas as opas
import yaqc_cmds.hardware.filters as filters
from yaqc_cmds.somatic import _wt5

all_hardwares = opas.hardwares + spectrometers.hardwares + delays.hardwares + filters.hardwares


### define ####################################################################


module_name = "SCAN"


### custom classes ############################################################


class Axis:
    def __init__(self, units_kind, axis_index):
        self.units_kind = units_kind
        if self.units_kind == "energy":
            self.units = "wn"
            initial_start = 1500
            initial_stop = 1200
        elif self.units_kind == "delay":
            self.units = "ps"
            initial_start = -1
            initial_stop = 1
        elif self.units_kind == "angle":
            self.units = "deg"
            initial_start = 0.0
            initial_stop = 360.0
        else:
            raise ValueError(f"unexpected units kind: {self.units_kind}")
        self.widget = pw.InputTable()
        self.widget.add(str(axis_index) + " (" + self.units_kind + ")", None)
        # start
        self.start = pc.Number(initial_value=initial_start, units=self.units)
        self.start.set_disabled_units(True)
        self.widget.add("Initial", self.start)
        # stop
        self.stop = pc.Number(initial_value=initial_stop, units=self.units)
        self.stop.set_disabled_units(True)
        self.widget.add("Final", self.stop)
        # number
        self.number = pc.Number(initial_value=51, decimals=0)
        self.widget.add("Number", self.number)
        # hardwares
        if self.units_kind == "energy":
            hardware_objs = opas.hardwares + spectrometers.hardwares
        elif self.units_kind == "delay":
            hardware_objs = delays.hardwares
        elif self.units_kind == "angle":
            hardware_objs = filters.hardwares
        self.hardwares = {}
        for hw in hardware_objs:
            checkbox = pc.Bool()
            self.widget.add(hw.name, checkbox)
            self.hardwares[hw.name] = checkbox

    def get_name(self):
        return "=".join([key for key in self.hardwares if self.hardwares[key].read()])

    def hide(self):
        self.widget.hide()


class Constant:
    def __init__(self):
        self.widget = pw.InputTable()
        self.widget.add("Constant", None)
        # hardware name
        allowed_values = [h.name for h in all_hardwares]
        self.hardware_name_combo = pc.Combo(allowed_values=allowed_values)
        self.hardware_name_combo.write(spectrometers.hardwares[0].name)
        # self.hardware_name_combo.set_disabled(True)
        self.widget.add("Hardware", self.hardware_name_combo)
        # expression
        opanames = [h.name for h in opas.hardwares]
        self.expression = pc.String(initial_value="+".join(opanames))
        self.widget.add("Expression", self.expression)

    def get_name(self):
        return self.hardware_name_combo.read()

    def hide(self):
        self.widget.hide()


### Worker ####################################################################


class Worker(acquisition.Worker):
    def process(self, scan_folder):
        with _wt5.data_container as data:
            # decide which channels to make plots for
            main_channel = self.aqn.read("processing", "main channel")
            if self.aqn.read("processing", "process all channels"):
                channels = data.channel_names
            else:
                channels = [main_channel]
            # make figures for each channel
            data_path = pathlib.Path(_wt5.data_container.data_filepath)
            data_folder = data_path.parent
            # make all images
            for channel_name in channels:
                channel_path = data_folder / channel_name
                output_path = data_folder
                if data.ndim > 2:
                    output_path = channel_path
                    channel_path.mkdir()
                channel_index = data.channel_names.index(channel_name)
                image_fname = channel_name
                if data.ndim == 1:
                    outs = wt.artists.quick1D(
                        data,
                        channel=channel_index,
                        autosave=True,
                        save_directory=output_path,
                        fname=image_fname,
                        verbose=False,
                    )
                else:
                    outs = wt.artists.quick2D(
                        data,
                        -1,
                        -2,
                        channel=channel_index,
                        autosave=True,
                        save_directory=output_path,
                        fname=image_fname,
                        verbose=False,
                    )
                if channel_name == main_channel:
                    outputs = outs
            # get output image
            if len(outputs) == 1:
                output_image_path = outputs[0]
            else:
                output_image_path = output_path / "animation.gif"
                wt.artists.stitch_to_animation(images=outputs, outpath=output_image_path)
            # upload
            self.upload(scan_folder, reference_image=str(output_image_path))

    def run(self):
        # axes
        axes = []
        for axis_name in self.aqn.read("scan", "axis names"):
            start = self.aqn.read(axis_name, "start")
            stop = self.aqn.read(axis_name, "stop")
            number = self.aqn.read(axis_name, "number")
            points = np.linspace(start, stop, int(number))
            units = self.aqn.read(axis_name, "units")
            axis = acquisition.Axis(points, units, axis_name)
            axes.append(axis)
        # constants
        constants = []
        for constant_name in self.aqn.read("scan", "constant names"):
            for hardware in all_hardwares:
                if hardware.name == constant_name:
                    units = hardware.units
                    if wt.units.kind(units) == "energy":
                        units = "wn"
                    break
            name = constant_name
            expression = self.aqn.read(constant_name, "expression")
            constant = acquisition.Constant(units, name, expression=expression, static=False)
            constants.append(constant)
        # do scan
        self.scan(axes, constants)
        # finish
        if not self.stopped.read():
            self.finished.write(True)  # only if acquisition successfull


### GUI #######################################################################


class GUI(acquisition.GUI):
    def add_axis(self, units_kind):
        axis = Axis(units_kind, len(self.axes))
        self.axes_container_widget.layout().addWidget(axis.widget)
        self.axes.append(axis)

    def add_buttons(self):
        colors = g.colors_dict.read()
        # layout
        button_container = QtWidgets.QWidget()
        button_container.setLayout(QtWidgets.QHBoxLayout())
        button_container.layout().setMargin(0)
        # remove
        remove_button = QtWidgets.QPushButton()
        remove_button.setText("REMOVE")
        remove_button.setMinimumHeight(25)
        StyleSheet = "QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}".replace(
            "custom_color", colors["stop"]
        )
        remove_button.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(remove_button)
        # add
        add_button = QtWidgets.QPushButton()
        add_button.setText("ADD")
        add_button.setMinimumHeight(25)
        StyleSheet = "QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}".replace(
            "custom_color", colors["set"]
        )
        add_button.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(add_button)
        # finish
        self.layout.addWidget(button_container)
        return [add_button, remove_button]

    def add_constant(self):
        # if len(self.constants) == 1: return  # temporary...
        constant = Constant()
        self.constants_container_widget.layout().addWidget(constant.widget)
        self.constants.append(constant)

    def create_frame(self):
        # axes
        self.axes = []
        input_table = pw.InputTable()
        input_table.add("Axes", None)
        self.layout.addWidget(input_table)
        self.axes_container_widget = QtWidgets.QWidget()
        self.axes_container_widget.setLayout(QtWidgets.QVBoxLayout())
        self.axes_container_widget.layout().setMargin(0)
        self.layout.addWidget(self.axes_container_widget)
        add_energy_axis_button = pw.SetButton("ADD ENERGY AXIS")
        add_energy_axis_button.clicked.connect(lambda: self.add_axis("energy"))
        self.layout.addWidget(add_energy_axis_button)
        add_delay_axis_button = pw.SetButton("ADD DELAY AXIS")
        add_delay_axis_button.clicked.connect(lambda: self.add_axis("delay"))
        self.layout.addWidget(add_delay_axis_button)
        add_delay_axis_button = pw.SetButton("ADD ANGLE AXIS")
        add_delay_axis_button.clicked.connect(lambda: self.add_axis("angle"))
        self.layout.addWidget(add_delay_axis_button)
        remove_axis_button = pw.SetButton("REMOVE AXIS", "stop")
        remove_axis_button.clicked.connect(self.remove_axis)
        self.layout.addWidget(remove_axis_button)
        # constants
        self.constants = []
        input_table = pw.InputTable()
        input_table.add("Constants", None)
        self.layout.addWidget(input_table)
        self.constants_container_widget = QtWidgets.QWidget()
        self.constants_container_widget.setLayout(QtWidgets.QVBoxLayout())
        self.constants_container_widget.layout().setMargin(0)
        self.layout.addWidget(self.constants_container_widget)
        add_constant_button, remove_constant_button = self.add_buttons()
        add_constant_button.clicked.connect(self.add_constant)
        remove_constant_button.clicked.connect(self.remove_constant)
        # processing
        input_table = pw.InputTable()
        input_table.add("Processing", None)
        channel_names = list(yaqc_cmds.sensors.get_channels_dict().keys())
        if (
            "main_channel" not in self.state.keys()
            or self.state["main_channel"] not in channel_names
        ):
            self.state["main_channel"] = channel_names[0]
        self.channel_combo = pc.Combo(
            allowed_values=channel_names,
            initial_value=self.state["main_channel"],
        )
        self.channel_combo.updated.connect(self.save_state)
        input_table.add("Main Channel", self.channel_combo)
        if "process_all_channels" not in self.state.keys():
            self.state["process_all_channels"] = False
        self.process_all_channels = pc.Bool(initial_value=self.state["process_all_channels"])
        self.process_all_channels.updated.connect(self.save_state)
        input_table.add("Process All Channels", self.process_all_channels)
        self.layout.addWidget(input_table)

    def load(self, aqn_path):
        # clear old
        for axis in self.axes:
            axis.hide()
        for constant in self.constants:
            constant.hide()
        self.axes = []
        self.channels = []
        self.constants = []
        # read new
        aqn = wt.kit.INI(aqn_path)
        # axes
        axis_names = aqn.read("scan", "axis names")
        for axis_index, axis_name in enumerate(axis_names):
            units = aqn.read(axis_name, "units")
            units_kind = None
            for kind, d in wt.units.dicts.items():
                if units in d.keys():
                    units_kind = kind
            axis = Axis(units_kind, axis_index)
            axis.start.write(aqn.read(axis_name, "start"))
            axis.stop.write(aqn.read(axis_name, "stop"))
            axis.number.write(aqn.read(axis_name, "number"))
            hardwares = aqn.read(axis_name, "hardware")
            for hardware in hardwares:
                axis.hardwares[hardware].write(True)
            self.axes.append(axis)
            self.axes_container_widget.layout().addWidget(axis.widget)
        # constants
        constant_names = aqn.read("scan", "constant names")
        for constant_index, constant_name in enumerate(constant_names):
            constant = Constant()
            constant.hardware_name_combo.write(aqn.read(constant_name, "hardware"))
            constant.expression.write(aqn.read(constant_name, "expression"))
            self.constants.append(constant)
            self.constants_container_widget.layout().addWidget(constant.widget)
        # processing
        try:
            self.channel_combo.write(aqn.read("processing", "main channel"))
        except ValueError:
            pass  # TODO: log warning or something
        self.process_all_channels.write(aqn.read("processing", "process all channels"))
        # allow record to load settings
        # self.device_widget.load(aqn_path)

    def on_device_settings_updated(self):
        self.channel_combo.set_allowed_values(record.control.channel_names)

    def remove_axis(self):
        # remove trailing axis
        if len(self.axes) > 0:
            axis = self.axes[-1]
            self.axes_container_widget.layout().removeWidget(axis.widget)
            axis.hide()
            self.axes.pop(-1)

    def remove_constant(self):
        # remove trailing constant
        if len(self.constants) > 0:
            constant = self.constants[-1]
            self.constants_container_widget.layout().removeWidget(constant.widget)
            constant.hide()
            self.constants.pop(-1)

    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        # general
        axis_names = str([str(a.get_name()) for a in self.axes]).replace("'", "")
        aqn.write("info", "description", "SCAN: {}".format(axis_names))
        aqn.add_section("scan")
        aqn.write("scan", "axis names", [a.get_name() for a in self.axes])
        aqn.write("scan", "constant names", [c.get_name() for c in self.constants])
        # axes
        for axis in self.axes:
            name = axis.get_name()
            aqn.add_section(name)
            aqn.write(name, "start", axis.start.read())
            aqn.write(name, "stop", axis.stop.read())
            aqn.write(name, "number", axis.number.read())
            aqn.write(name, "units", axis.units)
            hardwares = []
            for key, bool_mutex in axis.hardwares.items():
                if bool_mutex.read():
                    hardwares.append(key)
            aqn.write(name, "hardware", hardwares)
        # constants
        for constant in self.constants:
            name = constant.get_name()
            aqn.add_section(name)
            aqn.write(name, "hardware", constant.hardware_name_combo.read())
            aqn.write(name, "expression", constant.expression.read())
        # processing
        aqn.add_section("processing")
        aqn.write("processing", "main channel", self.channel_combo.read())
        aqn.write("processing", "process all channels", self.process_all_channels.read())
        # allow devices to write settings
        # self.device_widget.save(aqn_path)

    def save_state(self):
        self.state["main_channel"] = self.channel_combo.read()
        self.state["process_all_channels"] = self.process_all_channels.read()
        super().save_state()


def load():
    return True


def mkGUI():
    global gui
    gui = GUI(module_name)

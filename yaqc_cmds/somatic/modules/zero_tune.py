### import ####################################################################


import numpy as np

import matplotlib

matplotlib.pyplot.ioff()

from PySide2 import QtWidgets
import WrightTools as wt
import attune

import yaqc_cmds.project.project_globals as g
import yaqc_cmds.project.classes as pc
import yaqc_cmds.project.widgets as pw
import yaqc_cmds.somatic.acquisition as acquisition
from yaqc_cmds.somatic.modules.scan import Axis as ScanAxisGUI
from yaqc_cmds.somatic.modules.scan import Constant

import yaqc_cmds.hardware.spectrometers as spectrometers
import yaqc_cmds.hardware.delays as delays
import yaqc_cmds.hardware.opas as opas
import yaqc_cmds.hardware.filters.filters as filters

all_hardwares = opas.hardwares + spectrometers.hardwares + delays.hardwares + filters.hardwares
import yaqc_cmds.devices.devices as devices


### define ####################################################################


module_name = "ZERO TUNE"


### Worker ####################################################################


class Worker(acquisition.Worker):
    def process(self, scan_folder):
        data_path = wt.kit.glob_handler(".data", folder=str(scan_folder))[0]
        data = wt.data.from_Yaqc_cmds(data_path)
        delays = self.aqn.read("delay", "delays")
        channel_name = self.aqn.read("processing", "channel")
        transform = list(data.axis_expressions)[:2]
        for axis in data.axis_expressions:
            if axis not in transform:
                if level:
                    data.level(axis, 0, 5)
                data.moment(axis, channel)
                channel_name = -1
        for delay in delays:
            attune.workup.intensity(
                data,
                channel_name,
                delay,
                level=self.aqn.read("processing", "level"),
                gtol=self.aqn.read("processing", "gtol"),
                ltol=self.aqn.read("processing", "ltol"),
                save_directory=scan_folder,
            )

        # upload
        self.upload(scan_folder)

    def run(self):
        axes = []
        # OPA
        opa_name = self.aqn.read("opa", "opa")
        npts = self.aqn.read("opa", "npts")
        opa_names = [opa.name for opa in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        opa_hardware = opas.hardwares[opa_index]
        opa_friendly_name = opa_hardware.name
        curve = opa_hardware.curve.copy()
        curve.convert("wn")
        pts = np.linspace(curve.setpoints[:].min(), curve.setpoints[:].max(), int(npts))
        axis = acquisition.Axis(pts, "wn", opa_friendly_name, opa_friendly_name)
        axes.append(axis)
        # delay
        axis_name = "delay"
        start = self.aqn.read(axis_name, "start")
        stop = self.aqn.read(axis_name, "stop")
        number = self.aqn.read(axis_name, "number")
        points = np.linspace(start, stop, int(number))
        units = self.aqn.read(axis_name, "units")
        name = "=".join(self.aqn.read(axis_name, "delays"))
        axis = acquisition.Axis(points, units, name, name)
        axes.append(axis)

        constants = []
        for constant_name in self.aqn.read("scan", "constant names"):
            for hardware in all_hardwares:
                if hardware.name == constant_name:
                    units = hardware.units
                    if wt.units.kind(units) == "energy":
                        units = "wn"
                    break
            name = constant_name
            identity = expression = self.aqn.read(constant_name, "expression")
            constant = acquisition.Constant(
                units, name, identity, expression=expression, static=False
            )
            constants.append(constant)
        # do scan
        self.scan(axes, constants)
        # finish
        if not self.stopped.read():
            self.finished.write(True)  # only if acquisition successfull


### GUI #######################################################################


class GUI(acquisition.GUI):
    def create_frame(self):
        input_table = pw.InputTable()
        # opa combo
        allowed = [hardware.name for hardware in opas.hardwares]
        self.opa_combo = pc.Combo(allowed)
        input_table.add("OPA", None)
        input_table.add("OPA", self.opa_combo)
        self.npts_opa = pc.Number(decimals=0, initial_value=21)
        input_table.add("npts", self.npts_opa)
        # delay
        self.delay = ScanAxisGUI("delay", "")
        self.delay.start.write(-3)
        self.delay.stop.write(3)
        self.delay.number.write(21)
        input_table.add("Delay", None)
        self.layout.addWidget(input_table)
        self.layout.addWidget(self.delay.widget)
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
        self.channel_combo = pc.Combo(allowed_values=devices.control.channel_names)
        input_table.add("Channel", self.channel_combo)
        self.process_level = pc.Bool(initial_value=False)
        self.process_gtol = pc.Number(initial_value=0, decimals=5)
        self.process_ltol = pc.Number(initial_value=1e-2, decimals=5)
        input_table.add("level", self.process_level)
        input_table.add("gtol", self.process_gtol)
        input_table.add("ltol", self.process_ltol)
        # finish
        self.layout.addWidget(input_table)

    def add_constant(self):
        # if len(self.constants) == 1: return  # temporary...
        constant = Constant()
        self.constants_container_widget.layout().addWidget(constant.widget)
        self.constants.append(constant)

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

    def load(self, aqn_path):
        for constant in self.constants:
            constant.hide()
        self.constants = []
        aqn = wt.kit.INI(aqn_path)
        self.opa_combo.write(aqn.read("opa", "opa"))
        self.npts_opa.write(aqn.read("opa", "npts"))
        self.channel_combo.write(aqn.read("processing", "channel"))
        self.process_level.write(aqn.read("process", "level"))
        self.process_gtol.write(aqn.read("process", "gtol"))
        self.process_ltol.write(aqn.read("process", "ltol"))
        self.delay.start.write(aqn.read("delay", "start"))
        self.delay.stop.write(aqn.read("delay", "stop"))
        self.delay.number.write(aqn.read("delay", "number"))
        for key, mutex in self.delay.hardwares.items():
            mutex.write(key in aqn.read("delay", "delays"))
        # constants
        constant_names = aqn.read("scan", "constant names")

        for constant_index, constant_name in enumerate(constant_names):
            constant = Constant()
            constant.hardware_name_combo.write(aqn.read(constant_name, "hardware"))
            constant.expression.write(aqn.read(constant_name, "expression"))
            self.constants.append(constant)
            self.constants_container_widget.layout().addWidget(constant.widget)
        # allow devices to load settings
        self.device_widget.load(aqn_path)

    def remove_constant(self):
        # remove trailing constant
        if len(self.constants) > 0:
            constant = self.constants[-1]
            self.constants_container_widget.layout().removeWidget(constant.widget)
            constant.hide()
            self.constants.pop(-1)

    def on_device_settings_updated(self):
        self.channel_combo.set_allowed_values(devices.control.channel_names)

    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        aqn.add_section("opa")
        aqn.write("opa", "opa", self.opa_combo.read())
        aqn.write("opa", "npts", self.npts_opa.read())
        aqn.add_section("delay")
        aqn.write("delay", "start", self.delay.start.read())
        aqn.write("delay", "stop", self.delay.stop.read())
        aqn.write("delay", "number", self.delay.number.read())
        aqn.write("delay", "units", self.delay.units)
        hardwares = []
        for key, bool_mutex in self.delay.hardwares.items():
            if bool_mutex.read():
                hardwares.append(key)
        aqn.write("delay", "delays", hardwares)
        aqn.write(
            "info",
            "description",
            "{} {} zero tune".format(self.opa_combo.read(), hardwares),
        )
        # constants
        aqn.add_section("scan")
        aqn.write("scan", "constant names", [c.get_name() for c in self.constants])
        for constant in self.constants:
            name = constant.get_name()
            aqn.add_section(name)
            aqn.write(name, "hardware", constant.hardware_name_combo.read())
            aqn.write(name, "expression", constant.expression.read())
        aqn.add_section("processing")
        aqn.write("processing", "channel", self.channel_combo.read())
        aqn.write("processing", "level", self.process_level.read())
        aqn.write("processing", "gtol", self.process_gtol.read())
        aqn.write("processing", "ltol", self.process_ltol.read())
        # allow devices to write settings
        self.device_widget.save(aqn_path)


def load():
    return True


def mkGUI():
    global gui
    gui = GUI(module_name)

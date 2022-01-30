# --- import --------------------------------------------------------------------------------------


import pathlib
import time

import appdirs
import toml

import WrightTools as wt
import yaqc

import yaqc_cmds.__main__
import yaqc_cmds.project.project_globals as g
import yaqc_cmds.project.widgets as pw
import yaqc_cmds.project.classes as pc
import yaqc_cmds.hardware.hardware as hw


# --- driver --------------------------------------------------------------------------------------


class Driver(hw.Driver):
    def __init__(self, *args, **kwargs):
        self.yaqd_port = kwargs["yaqd_port"]
        self.yaqd_host = kwargs.get("yaqd_host", "127.0.0.1")
        self.motor = yaqc.Client(self.yaqd_port, host=self.yaqd_host)
        self.native_units = self.motor.get_units()
        hw.Driver.__init__(self, *args, **kwargs)
        id_ = self.motor.id()
        if id_["model"] is not None:
            self.hardware.model = id_["model"]
        elif id_["kind"].startswith("fake"):
            self.hardware.model = "fake"
        else:
            self.hardware.model = id_["kind"]

        self.update_recorded()
        self.busy.write(self.is_busy())

    def home(self):
        self.motor.home()
        self.wait_until_still()

    def is_busy(self):
        return self.motor.busy()

    def update_recorded(self):
        self.recorded.clear()
        self.recorded[self.name] = [
            self.position,
            self.native_units,
            1.0,
            self.label.read(),
            False,
        ]

    def set_position(self, destination, units=None):
        if units:
            destination = wt.units.convert(destination, units, self.native_units)
        self.motor.set_position(destination)
        self.wait_until_still()
        self.get_position()
        self.save_status()

    def get_position(self):
        position = self.motor.get_position()
        self.position.write(position, self.native_units)
        return position


# --- gui -----------------------------------------------------------------------------------------


class GUI(hw.GUI):
    def initialize(self):
        self.layout.addWidget(self.scroll_area)
        # attributes
        self.attributes_table.add("Label", self.hardware.label)
        self.scroll_layout.addWidget(self.attributes_table)
        # horizontal line
        self.scroll_layout.addWidget(pw.line("H"))
        # home button
        self.home_button = pw.SetButton("HOME", "advanced")
        self.scroll_layout.addWidget(self.home_button)
        self.home_button.clicked.connect(self.on_home)
        g.queue_control.disable_when_true(self.home_button)
        # finish
        self.scroll_layout.addStretch(1)
        self.layout.addStretch(1)
        self.hardware.update_ui.connect(self.update)

    def on_home(self):
        self.driver.hardware.q.push("home")

    def update(self):
        pass


# --- hardware ------------------------------------------------------------------------------------


class Hardware(hw.Hardware):
    def __init__(self, *arks, **kwargs):
        self.kind = "delay"
        hw.Hardware.__init__(self, *arks, **kwargs)
        self.label = pc.String(self.name, display=True)


# --- import --------------------------------------------------------------------------------------


conf = yaqc_cmds.__main__.config
hardwares, gui, advanced_gui = hw.import_hardwares(
    conf.get("hardware", {}).get("delays", {}),
    name="Delays",
    Driver=Driver,
    GUI=GUI,
    Hardware=Hardware,
)

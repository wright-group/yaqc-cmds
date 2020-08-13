# --- import --------------------------------------------------------------------------------------


import pathlib

import appdirs
import toml

import WrightTools as wt

import project.project_globals as g
import project.widgets as pw
import project.classes as pc
import hardware.hardware as hw


# --- driver --------------------------------------------------------------------------------------


class Driver(hw.Driver):
    def __init__(self, *args, **kwargs):
        self.motor_units = kwargs.pop("motor_units")
        hw.Driver.__init__(self, *args, **kwargs)
        self.factor = self.hardware.factor
        self.factor.write(kwargs["factor"])
        self.motor_limits = self.hardware.motor_limits
        self.motor_position = self.hardware.motor_position
        self.zero_position = self.hardware.zero_position
        self.recorded["_".join([self.name, "zero"])] = [
            self.zero_position,
            "mm",
            0.001,
            self.name[-1],
            True,
        ]
        self.native_per_mm = 1

    def get_state(self):
        state = super().get_state()
        state["zero_position"] = self.zero_position.read(self.motor_units)
        return state

    def load_state(self, state):
        super().load_state(state)
        self.hardware.zero_position.write(state.get("zero_postion", 0))

    def set_motor_position(self, motor_position):
        self.motor_position.write(motor_position)

    def set_offset(self, offset):
        # update zero
        offset_from_here = offset - self.offset.read(self.native_units)
        offset_mm = offset_from_here / (self.native_per_mm * self.factor.read())
        new_zero = self.zero_position.read("mm") + offset_mm
        self.set_zero(new_zero)
        self.offset.write(offset, self.native_units)
        # return to old position
        destination = self.hardware.destination.read(self.native_units)
        self.set_position(destination)

    def update_recorded(self):
        self.recorded.clear()
        self.recorded["d" + str(self.index)] = [
            self.position,
            self.native_units,
            1.0,
            self.label.read(),
            False,
        ]
        self.recorded["d" + str(self.index) + "_position"] = [
            self.motor_position,
            "mm",
            1.0,
            self.label.read(),
            False,
        ]
        self.recorded["d" + str(self.index) + "_zero"] = [
            self.zero_position,
            "mm",
            1.0,
            self.label.read(),
            False,
        ]

    def set_zero(self, new_zero):
        pass


# --- gui -----------------------------------------------------------------------------------------


class GUI(hw.GUI):
    def initialize(self):
        self.layout.addWidget(self.scroll_area)
        # attributes
        self.attributes_table.add("Label", self.hardware.label)
        self.attributes_table.add("Factor", self.hardware.factor)
        self.scroll_layout.addWidget(self.attributes_table)
        # mm input table
        input_table = pw.InputTable()
        input_table.add("Motor Position", None)
        input_table.add("Current", self.hardware.motor_position)
        self.motor_destination = self.hardware.motor_position.associate(display=False)
        input_table.add("Destination", self.motor_destination)
        self.scroll_layout.addWidget(input_table)
        # set mm button
        self.set_motor_button = pw.SetButton("SET POSITION")
        self.scroll_layout.addWidget(self.set_motor_button)
        self.set_motor_button.clicked.connect(self.on_set_motor)
        g.queue_control.disable_when_true(self.set_motor_button)
        # zero input table
        input_table = pw.InputTable()
        input_table.add("Zero Position", None)
        input_table.add("Current", self.hardware.zero_position)
        self.zero_destination = self.hardware.zero_position.associate(display=False)
        input_table.add("Destination", self.zero_destination)
        self.scroll_layout.addWidget(input_table)
        # set zero button
        self.set_zero_button = pw.SetButton("SET ZERO")
        self.scroll_layout.addWidget(self.set_zero_button)
        self.set_zero_button.clicked.connect(self.on_set_zero)
        g.queue_control.disable_when_true(self.set_zero_button)
        # horizontal line
        self.scroll_layout.addWidget(pw.line("H"))
        # home button
        input_table = pw.InputTable()
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

    def on_set_motor(self):
        new_mm = self.motor_destination.read("mm")
        self.hardware.set_motor_position(new_mm, units="mm")

    def on_set_zero(self):
        new_zero = self.zero_destination.read("mm")
        self.driver.set_zero(new_zero)
        self.driver.offset.write(0)
        name = self.hardware.name
        g.coset_control.read().zero(name)
        self.driver.get_position()
        self.driver.save_status()

    def update(self):
        pass


# --- hardware ------------------------------------------------------------------------------------


class Hardware(hw.Hardware):
    def __init__(self, *arks, **kwargs):
        self.kind = "delay"
        self.factor = pc.Number(1, decimals=0)
        self.motor_limits = pc.NumberLimits(min_value=0, max_value=50, units="mm")
        self.motor_position = pc.Number(
            units="mm", display=True, limits=self.motor_limits
        )
        self.zero_position = pc.Number(display=True)
        hw.Hardware.__init__(self, *arks, **kwargs)
        self.label = pc.String(self.name, display=True)

    def set_motor_position(self, motor_position, units="mm"):
        # TODO: should probably support 'motor native units'
        self.q.push("set_motor_position", motor_position)


# --- import --------------------------------------------------------------------------------------


conf = pathlib.Path(appdirs.user_config_dir("pycmds", "pycmds")) / "config.toml"
conf = toml.load(conf)
hardwares, gui, advanced_gui = hw.import_hardwares(
    conf.get("hardware", {}).get("delays", {}),
    name="Delays",
    Driver=Driver,
    GUI=GUI,
    Hardware=Hardware,
)

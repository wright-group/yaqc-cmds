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
        self.motor_units = self.motor.get_units()
        if self.motor_units == "mm":
            self.motor_units = "mm_delay"
        self.native_units = kwargs.get("native_units", "ps")
        self.native_per_motor = float(wt.units.convert(1, self.motor_units, self.native_units))
        hw.Driver.__init__(self, *args, **kwargs)
        id_ = self.motor.id()
        if id_["model"] is not None:
            self.hardware.model = id_["model"]
        elif id_["kind"].startswith("fake"):
            self.hardware.model = "fake"
        else:
            self.hardware.model = id_["kind"]

        self.factor = self.hardware.factor
        self.factor.write(kwargs["factor"])
        self.motor_limits = self.hardware.motor_limits
        self.motor_limits.write(*self.motor.get_limits())
        self.motor_position = self.hardware.motor_position
        self.zero_position = self.hardware.zero_position
        self.set_zero(self.zero_position.read())
        self.update_recorded()

    def initialize(self):
        # This should be unnecessary at some point, once everything is yaq
        self.get_position()
        self.initialized.write(True)
        self.initialized_signal.emit()

    def home(self):
        self.motor.home()
        self.wait_until_still()

    def is_busy(self):
        return self.motor.busy()

    def get_position(self):
        position = self.motor.get_position()
        self.motor_position.write(position)
        delay = (
            (position - wt.units.convert(self.zero_position.read(), "mm_delay", self.motor_units))
            * self.native_per_motor
            * self.factor.read()
        )
        self.position.write(delay, self.native_units)
        return delay

    def get_state(self):
        state = super().get_state()
        state["zero_position"] = float(self.zero_position.read())
        return state

    def load_state(self, state):
        super().load_state(state)
        # called before self.zero_position aliases the hardware one
        self.hardware.zero_position.write(state.get("zero_position", 0))

    def set_motor_position(self, motor_position):
        print("set_motor_position", self.name, motor_position)
        self.motor.set_position(motor_position)
        while self.is_busy():
            time.sleep(0.01)
            self.get_position()
        self.get_position()

    def set_position(self, destination):
        destination_motor = wt.units.convert(
            self.zero_position.read(), "mm_delay", self.motor_units
        ) + destination / (self.native_per_motor * self.factor.read())
        self.set_motor_position(destination_motor)

    def set_offset(self, offset):
        print("delays set_offset", self.name, offset)
        # update zero
        offset_from_here = offset - self.offset.read(self.native_units)
        offset_motor = offset_from_here / (self.native_per_motor * self.factor.read())
        new_zero = (
            wt.units.convert(self.zero_position.read(), "mm_delay", self.motor_units)
            + offset_motor
        )
        self.set_zero(new_zero)
        self.offset.write(offset, self.native_units)
        print("new offset", self.name, self.offset.read())
        # return to old position
        destination = self.hardware.destination.read(self.native_units)
        print("new destination", self.name, destination)
        self.set_position(destination)

    def update_recorded(self):
        self.recorded.clear()
        self.recorded[self.name] = [
            self.position,
            self.native_units,
            1.0,
            self.label.read(),
            False,
        ]
        self.recorded[f"{self.name}_position"] = [
            self.motor_position,
            self.motor_units,
            1.0,
            self.label.read(),
            False,
        ]
        self.recorded[f"{self.name}_zero"] = [
            self.zero_position,
            self.motor_units,
            1.0,
            self.label.read(),
            False,
        ]

    def set_zero(self, new_zero):
        self.zero_position.write(new_zero)
        motor_min, motor_max = self.motor_limits.read()
        min_ = (motor_min - new_zero) * self.native_per_motor * self.factor.read()
        max_ = (motor_max - new_zero) * self.native_per_motor * self.factor.read()
        self.limits.write(min_, max_, self.native_units)
        self.get_position()


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
        print("on_set_new_zero", new_zero)
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
        self.factor = pc.Number(1, decimals=0, display=True)
        self.motor_limits = pc.NumberLimits(min_value=0, max_value=50, units="mm")
        self.motor_position = pc.Number(units="mm", display=True, limits=self.motor_limits)
        self.zero_position = pc.Number(display=True, units="mm", limits=self.motor_limits)
        hw.Hardware.__init__(self, *arks, **kwargs)
        self.label = pc.String(self.name, display=True)

    def set_motor_position(self, motor_position, units="mm"):
        # TODO: should probably support 'motor native units'
        self.q.push("set_motor_position", motor_position)


# --- import --------------------------------------------------------------------------------------


conf = yaqc_cmds.__main__.config
hardwares, gui, advanced_gui = hw.import_hardwares(
    conf.get("hardware", {}).get("delays", {}),
    name="Delays",
    Driver=Driver,
    GUI=GUI,
    Hardware=Hardware,
)

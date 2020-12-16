"""
Parent hardware class and associated.
"""
__all__ = ["Driver", "GUI", "Hardware", "import_hardwares"]


### import ####################################################################


import pathlib
import time
import collections

from PySide2 import QtCore
from PySide2 import QtWidgets

import appdirs
import toml

import WrightTools as wt

from yaqc_cmds.project import classes as pc
from yaqc_cmds.project import widgets as pw
from yaqc_cmds.project import project_globals as g


__here__ = pathlib.Path(__file__)


### driver ####################################################################


class Driver(pc.Driver):
    initialized_signal = QtCore.Signal()

    def __init__(self, hardware, **kwargs):
        pc.Driver.__init__(self)
        # basic attributes
        self.hardware = hardware
        self.enqueued = self.hardware.enqueued
        self.busy = self.hardware.busy
        self.name = self.hardware.name
        self.model = self.hardware.model
        self.serial = self.hardware.serial
        self.label = pc.String(kwargs["label"], display=True)
        self.native_units = kwargs["native_units"]
        self.state_filepath = (
            pathlib.Path(appdirs.user_data_dir("yaqc-cmds", "yaqc-cmds"))
            / "hardware"
            / f"{self.name}-state.toml"
        )
        self.state_filepath.parent.mkdir(parents=True, exist_ok=True)
        # mutex attributes
        self.limits = pc.NumberLimits(units=self.native_units)
        if self.state_filepath.exists():
            state = toml.load(self.state_filepath)
        else:
            state = {}
        self.offset = pc.Number(
            initial_value=0, units=self.native_units, name="Offset", display=True
        )
        self.load_state(state)
        # attributes for 'exposure'
        self.exposed = [self.position]
        self.recorded = collections.OrderedDict()
        print(self.name, type(self.name))
        self.recorded[self.name] = [
            self.position,
            self.native_units,
            1.0,
            self.label.read(),
            False,
        ]
        # self.queue_emptied.connect(self.save_status)

    def close(self):
        pass

    def get_position(self):
        self.update_ui.emit()

    def initialize(self):
        """
        May not accept arguments.
        """
        print("Driver initialize", self.name)
        self.label.updated.connect(self.on_label_updated)
        self.initialized.write(True)
        self.initialized_signal.emit()

    @QtCore.Slot()
    def on_label_updated(self):
        self.recorded[self.name] = [
            self.position,
            self.native_units,
            1.0,
            self.label.read(),
            False,
        ]

    def poll(self):
        """
        polling only gets enqueued by Hardware when not in module control
        """
        self.get_position()
        self.is_busy()

    def get_state(self):
        return {
            "position": float(self.position.read(self.native_units)),
            "display_units": self.position.units,
            "offset": float(self.offset.read()),
        }

    def save_status(self):
        print(self.name, "STATE", self.get_state())
        with open(self.state_filepath, "w") as f:
            toml.dump(self.get_state(), f)

    def load_state(self, state):
        self.position = pc.Number(
            initial_value=state.get("position", 0),
            units=self.native_units,
            name="Position",
            display=True,
            set_method="set_position",
            limits=self.limits,
        )
        self.position.set_units(state.get("display_units", self.native_units))
        self.offset.write(state.get("offset", 0))

    def set_offset(self, offset):
        self.offset.write(offset, self.native_units)

    def set_position(self, destination):
        time.sleep(0.01)  # rate limiter for virtual hardware behavior
        self.position.write(destination, self.native_units)
        self.get_position()
        self.save_status()

    def wait_until_still(self):
        while self.is_busy():
            self.get_position()
            time.sleep(0.01)
        self.get_position()


### gui #######################################################################


class GUI(QtCore.QObject):
    def __init__(self, hardware):
        """
        Runs after driver.__init__, but before driver.initialize.
        """
        QtCore.QObject.__init__(self)
        self.hardware = hardware
        self.driver = hardware.driver

    def close(self):
        pass

    def create_frame(self, layout):
        """
        Runs before initialize.
        """
        # layout
        layout.setMargin(5)
        self.layout = layout
        # scroll area
        scroll_container_widget = QtWidgets.QWidget()
        self.scroll_area = pw.scroll_area(show_bar=False)
        self.scroll_area.setWidget(scroll_container_widget)
        self.scroll_area.setMinimumWidth(300)
        self.scroll_area.setMaximumWidth(300)
        scroll_container_widget.setLayout(QtWidgets.QVBoxLayout())
        self.scroll_layout = scroll_container_widget.layout()
        self.scroll_layout.setMargin(5)
        # attributes table
        self.attributes_table = pw.InputTable()
        self.attributes_table.add("Attributes", None)
        name = pc.String(self.hardware.name, display=True)
        self.attributes_table.add("Name", name)
        model = pc.String(self.hardware.model, display=True)
        self.attributes_table.add("Model", model)
        serial = pc.String(self.hardware.serial, display=True)
        self.attributes_table.add("Serial", serial)
        self.position = self.hardware.position.associate()
        self.hardware.position.updated.connect(self.on_position_updated)
        self.attributes_table.add("Label", self.hardware.driver.label)
        self.attributes_table.add("Position", self.position)
        self.offset = self.hardware.offset.associate()
        self.hardware.offset.updated.connect(self.on_offset_updated)
        self.attributes_table.add("Offset", self.offset)
        # initialization
        if self.hardware.initialized.read():
            self.initialize()
        else:
            self.hardware.initialized_signal.connect(self.initialize)

    def initialize(self):
        """
        Runs only once the hardware is done initializing.
        """
        self.layout.addWidget(self.scroll_area)
        # attributes
        self.scroll_layout.addWidget(self.attributes_table)
        # stretch
        self.scroll_layout.addStretch(1)
        self.layout.addStretch(1)

    def on_offset_updated(self):
        new = self.hardware.offset.read(self.hardware.native_units)
        self.offset.write(new, self.hardware.native_units)

    def on_position_updated(self):
        new = self.hardware.position.read(self.hardware.native_units)
        self.position.write(new, self.hardware.native_units)


### hardware ##################################################################


hardwares = []


def all_initialized():
    # fires any time a hardware is initialized
    for hardware in hardwares:
        while not hardware.initialized.read():
            print(hardware.name, "not yet inited")
            time.sleep(0.1)
    # past here only runs when ALL hardwares are initialized
    g.hardware_initialized.write(True)


class Hardware(pc.Hardware):
    def __init__(self, *args, **kwargs):
        pc.Hardware.__init__(self, *args, **kwargs)
        self.driver.initialized_signal.connect(self.on_address_initialized)
        self.exposed = self.driver.exposed
        for obj in self.exposed:
            obj.updated.connect(self.update)
        self.recorded = self.driver.recorded
        self.offset = self.driver.offset
        self.position = self.exposed[0]
        self.native_units = self.driver.native_units
        self.destination = pc.Number(units=self.native_units, display=True)
        self.destination.write(self.position.read(self.native_units), self.native_units)
        self.limits = self.driver.limits
        hardwares.append(self)

    def close(self):
        self.q.push("save_status")
        pc.Hardware.close(self)

    def get_destination(self, output_units="same"):
        print("get_destination", self.name, self.destination.read(output_units))
        return self.destination.read(output_units=output_units)

    def get_position(self, output_units="same"):
        return self.position.read(output_units=output_units)

    def is_valid(self, destination, input_units=None):
        if input_units is None:
            pass
        else:
            destination = wt.units.converter(destination, input_units, self.native_units)
        min_value, max_value = self.limits.read(self.native_units)
        if min_value <= destination <= max_value:
            return True
        else:
            return False

    def on_address_initialized(self):
        self.destination.write(self.get_position(), self.native_units)
        # all_initialized()
        self.initialized_signal.emit()

    def poll(self, force=False):
        if force:
            self.q.push("poll")
            self.get_position()
        elif not g.queue_control.read():
            self.q.push("poll")
            self.get_position()

    def set_offset(self, offset, input_units=None):
        if input_units is None:
            pass
        else:
            offset = wt.units.converter(offset, input_units, self.native_units)
        # do nothing if new offset is same as current offset
        if offset == self.offset.read(self.native_units):
            return
        self.q.push("set_offset", offset)

    def set_position(self, destination, input_units=None, force_send=False):
        if input_units is None:
            pass
        else:
            destination = wt.units.converter(destination, input_units, self.native_units)
        # do nothing if new destination is same as current destination
        if destination == self.destination.read(self.native_units):
            if not force_send:
                return
        self.destination.write(destination, self.native_units)
        self.q.push("set_position", destination)

    @property
    def units(self):
        return self.position.units


### import method #############################################################


def import_hardwares(config, name, Driver, GUI, Hardware):
    hardwares = []
    for hw_name, section in config.items():
        if section.get("enable", True):
            # initialization arguments
            kwargs = collections.OrderedDict()
            kwargs.update(section)
            for option in ["__name__", "enable", "model", "serial", "path"]:
                kwargs.pop(option, None)
            model = section.get("model", "yaq")
            hardware = Hardware(Driver, kwargs, GUI, name=hw_name, model=model)
            hardwares.append(hardware)
    gui = pw.HardwareFrontPanel(hardwares, name=name)
    advanced_gui = pw.HardwareAdvancedPanel(hardwares, gui.advanced_button)
    return hardwares, gui, advanced_gui

"""
Parent hardware class and associated.
"""


### import ####################################################################


import time
import collections

from PySide2 import QtCore
from PySide2 import QtWidgets

import WrightTools as wt
import yaqc

import project.classes as pc
import project.widgets as pw
import project.project_globals as g


### gui #######################################################################


class GUI(QtCore.QObject):
    def __init__(self, hardware):
        """
        Runs after driver.__init__, but before driver.initialize.
        """
        QtCore.QObject.__init__(self)
        self.hardware = hardware

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
        self.attributes_table.add("Label", self.hardware.label)
        self.attributes_table.add("Position", self.position)
        self.offset = self.hardware.offset.associate()
        self.hardware.offset.updated.connect(self.on_offset_updated)
        self.attributes_table.add("Offset", self.offset)

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


class Hardware(yaqc.Client):
    def __init__(self, name: str, port: int, host: str="localhost"):
        super().__init__(port=port, host=host)
        self.name = name
        self.native_units: str = self.get_units()
        # mutex attributes
        self.limits = pc.NumberLimits(units=self.native_units)
        self.position = pc.Number(
            initial_value=self.send("get_position"),
            units=self.native_units,
            name="Position",
            display=True,
            set_method="set_position",
            limits=self.limits,
        )
        self.offset = pc.Number(units=self.native_units, name="Offset", display=True)
        # attributes for 'exposure'
        self.exposed = [self.position]
        self.recorded = collections.OrderedDict()
        self.recorded[self.name] = [
            self.position,
            self.native_units,
            1.0,
            self.name,
        ]
        for key,value in self.id().items():
            setattr(self, key, str(value))
        self._busy_obj = pc.Busy()
        self.gui = GUI(self)
        self.label = pc.String(self.name)



    def get_destination(self, output_units="same"):
        return self.destination.read(output_units=output_units)

    def get_position(self, output_units="same"):
        return self.position.read(output_units=output_units)

    def set_offset(self, offset, input_units=None):
        if input_units is None:
            pass
        else:
            offset = wt.units.converter(offset, input_units, self.native_units)
        # do nothing if new offset is same as current offset
        if offset == self.offset.read(self.native_units):
            return

    def set_position(self, destination, input_units=None):
        if input_units is None:
            pass
        else:
            destination = wt.units.converter(destination, input_units, self.native_units)
        # do nothing if new destination is same as current destination
        if destination == self.destination.read(self.native_units):
            if not force_send:
                return
        self.destination.write(destination, self.native_units)

    @property
    def units(self):
        return self.position.units

    @property
    def busy_obj(self):
        self._busy = self.send("busy")
        self._busy_obj.write(self._busy)
        return self._busy_obj



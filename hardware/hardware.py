"""
Parent hardware class and associated.
"""


### import ####################################################################


import os
import imp
import time
import collections

from PyQt4 import QtCore
from PyQt4 import QtGui

import WrightTools as wt

import project.classes as pc
import project.widgets as pw
import project.project_globals as g


### driver ####################################################################


class Driver(pc.Driver):
    initialized_signal = QtCore.pyqtSignal()

    def __init__(self, hardware, native_units=None, **kwargs):
        pc.Driver.__init__(self)
        # basic attributes
        self.hardware = hardware
        self.enqueued = self.hardware.enqueued
        self.busy = self.hardware.busy
        self.name = self.hardware.name
        self.native_units = native_units
        # mutex attributes
        self.limits = pc.NumberLimits(units=self.native_units)
        self.position = pc.Number(units=self.native_units, name='Position',
                                  display=True, set_method='set_position',
                                  limits=self.limits)
        self.offset = pc.Number(units=self.native_units, name='Offset',
                                display=True)
        # attributes for 'exposure'
        self.exposed = [self.position]
        self.recorded = collections.OrderedDict()
        self.recorded[self.name] = [self.position, self.native_units, 1., self.name, False] 

    def close(self):
        pass

    def get_position(self):
        self.update_ui.emit()

    def initialize(self):
        """
        May not accept arguments.
        """
        self.initialized.write(True)
        self.initialized_signal.emit()

    def poll(self):
        """
        polling only gets enqueued by Hardware when not in module control
        """
        self.get_position()
        self.is_busy()

    def set_offset(self, offset):
        # TODO:
        pass

    def set_position(self, destination):
        time.sleep(0.1)  # rate limiter for virtual hardware behavior
        self.position.write(destination)
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
        scroll_container_widget = QtGui.QWidget()
        self.scroll_area = pw.scroll_area(show_bar=False)
        self.scroll_area.setWidget(scroll_container_widget)
        self.scroll_area.setMinimumWidth(300)
        self.scroll_area.setMaximumWidth(300)
        scroll_container_widget.setLayout(QtGui.QVBoxLayout())
        self.scroll_layout = scroll_container_widget.layout()
        self.scroll_layout.setMargin(5)
        # attributes table
        self.attributes_table = pw.InputTable()
        self.attributes_table.add('Attributes', None)
        name = pc.String(self.hardware.name, display=True)
        self.attributes_table.add('Name', name)
        model = pc.String(self.hardware.model, display=True)
        self.attributes_table.add('Model', model)
        serial = pc.String(self.hardware.serial, display=True)
        self.attributes_table.add('Serial', serial)
        self.position = self.hardware.position.associate()
        self.hardware.position.updated.connect(self.on_position_updated)
        self.attributes_table.add('Position', self.position)
        self.attributes_table.add('Offset', self.hardware.offset)
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
        
    def on_position_updated(self):
        new = self.hardware.position.read(self.hardware.native_units)
        self.position.write(new, self.hardware.native_units)


### hardware ##################################################################


hardwares = []
def all_initialized():
    time.sleep(1)
    # fires any time a hardware is initialized
    for hardware in hardwares:
        if not hardware.initialized.read():
            return
    # past here only runs when ALL hardwares are initialized
    g.hardware_initialized.write(True)


class Hardware(pc.Hardware):

    def __init__(self, *args, **kwargs):
        pc.Hardware.__init__(self, *args, **kwargs)
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
        self.driver.initialized_signal.connect(self.on_address_initialized)
        hardwares.append(self)

    def get_destination(self, output_units='same'):
        return self.destination.read(output_units=output_units)

    def get_position(self, output_units='same'):
        return self.position.read(output_units=output_units)

    def is_valid(self, destination, input_units=None):
        if input_units is None:
            pass
        else:
            destination = wt.units.converter(destination,
                                             input_units,
                                             self.native_units)
        min_value, max_value = self.limits.read(self.native_units)
        if min_value <= destination <= max_value:
            return True
        else:
            return False
            
    def on_address_initialized(self):
        self.destination.write(self.get_position(), self.native_units)
        all_initialized()
        self.initialized_signal.emit()

    def poll(self, force=False):
        if force:
            self.q.push('poll')
            self.get_position()
        elif not g.queue_control.read():
            self.q.push('poll')
            self.get_position()
            
    def set_offset(self, offset, input_units=None):
        if input_units is None:
            pass
        else:
            offset = wt.units.converter(offset,
                                        input_units,
                                        self.native_units)
        # do nothing if new offset is same as current offset
        if offset == self.offset.read(self.native_units):
            return
        self.q.push('set_offset', [offset])

    def set_position(self, destination, input_units=None, force_send=False):
        if input_units is None:
            pass
        else:
            destination = wt.units.converter(destination,
                                             input_units,
                                             self.native_units)
        # do nothing if new destination is same as current destination
        if destination == self.destination.read(self.native_units):
            if not force_send:
                return
        self.destination.write(destination, self.native_units)
        self.q.push('set_position', destination)

    @property
    def units(self):
        return self.position.units


### import method #############################################################


def import_hardwares(ini_path, name, Driver, GUI, Hardware):
    ini = wt.kit.INI(ini_path)
    hardwares = []
    for section in ini.sections:
        if ini.read(section, 'enable'):
            # initialization arguments
            kwargs = collections.OrderedDict()
            for option in ini.get_options(section):
                if option in ['enable', 'model', 'serial', 'path']:
                    continue
                else:
                    kwargs[option] = ini.read(section, option)            
            model = ini.read(section, 'model')
            if model == 'Virtual':
                hardware = Hardware(Driver, kwargs, GUI, name=section, model='Virtual')
            else:
                path = os.path.abspath(ini.read(section, 'path'))
                fname = os.path.basename(path).split('.')[0]
                mod = imp.load_source(fname, path)
                cls = getattr(mod, 'Driver')
                gui = getattr(mod, 'GUI')
                serial = ini.read(section, 'serial')
                hardware = Hardware(cls, kwargs, gui, name=section, model=model, serial=serial)
            hardwares.append(hardware)
    gui = pw.HardwareFrontPanel(hardwares, name=name)
    advanced_gui = pw.HardwareAdvancedPanel(hardwares, gui.advanced_button)
    return hardwares, gui, advanced_gui

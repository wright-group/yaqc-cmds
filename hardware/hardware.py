"""
Parent hardware class and associated.
"""


### import ####################################################################


import time
import collections

from PyQt4 import QtCore
from PyQt4 import QtGui

import WrightTools as wt

import project.classes as pc 
import project.project_globals as g


### driver ####################################################################


class Driver(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    queue_emptied = QtCore.pyqtSignal()
    initialized_signal = QtCore.pyqtSignal()

    def __init__(self, enqueued_obj, busy_obj, name, native_units=None):
        QtCore.QObject.__init__(self)
        # basic attributes
        self.enqueued = enqueued_obj
        self.busy = busy_obj
        self.name = name
        self.native_units = native_units
        # mutex attributes
        self.limits = pc.NumberLimits(units=self.native_units)
        self.position = pc.Number(units=self.native_units, name='Position',
                                  display=True, set_method='set_position')
        self.offset = pc.Number(units=self.native_units, name='Offset')
        self.initialized = pc.Bool()
        # attributes for 'exposure'
        self.exposed = [self.position]
        self.recorded = collections.OrderedDict()

    def check_busy(self, inputs):
        """
        decides if the hardware is done and handles writing of 'busy' to False
        """
        # must always write busy whether answer is True or False
        if self.is_busy():
            time.sleep(0.01)  # don't loop like crazy
            self.busy.write(True)
        elif self.enqueued.read():
            time.sleep(0.1)  # don't loop like crazy
            self.busy.write(True)
        else:
            self.busy.write(False)
            self.update_ui.emit()

    def close(self):
        pass

    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        """
        accepts queued signals from 'queue' (address using q method) \n
        string method, list inputs
        """
        self.update_ui.emit()
        if g.debug.read():
            print(self.name, 'dequeue:', method, inputs)
        # execute method
        method = str(method)  # method passed as qstring
        if method == 'close':
            self.close()
        elif method == 'set_position':
            self.set_position(inputs[0])
        else:
            getattr(self, method)(inputs)
        # remove method from enqueued
        self.enqueued.pop()
        if not self.enqueued.read():
            self.queue_emptied.emit()
            self.check_busy([])
            self.update_ui.emit()

    def get_position(self):
        self.update_ui.emit()

    def initialize(self, inputs):
        # TODO: rewrite
        self.recorded[self.name] = [self.position, self.native_units, 1., self.name, False] 
        g.logger.log('info', self.name + ' Initializing', message=str(inputs))
        if g.debug.read():
            print(self.name, 'initialization complete')
        self.initialized_signal.emit()

    def is_busy(self):
        return False

    def poll(self, inputs):
        """
        polling only gets enqueued by Hardware when not in module control
        """
        self.get_position()
        self.is_busy()

    def set_offset(self, inputs):
        self.ctrl.set_offset(inputs[0])
        self.get_position()

    def set_position(self, destination):
        time.sleep(0.1)
        self.position.write(destination)
        self.get_position()


### gui #######################################################################


class GUI(QtCore.QObject):
    
    def __init__(self, hardware):
        QtCore.QObject.__init__(self)
        self.hardware = hardware
        self.driver = hardware.driver
    
    def close(self):
        pass
    
    def create_frame(self, layout):
        layout.setMargin(5)
        self.layout = layout
        self.frame = QtGui.QWidget()
        self.frame.setLayout(self.layout)
    
    def initialize(self):
        pass


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


class Hardware(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    initialized_signal = QtCore.pyqtSignal()

    def __init__(self, driver_class, driver_arguments, gui_class,
                 name, model, serial=None):
        """
        Hardware representation object living in the main thread.
        
        Parameters
        driver_class : Driver class
            Class of driver.
        driver_arguments : list
            Arguments passed to driver upon initialization.
        name : string
            Name. Must be unique.
        model : string
            Model. Need not be unique.
        serial : string or None (optional)
            Serial, if desired. Default is None.
        """
        QtCore.QObject.__init__(self)
        self.name = name
        self.model = model
        self.serial = serial
        # create objects
        self.thread = QtCore.QThread()
        self.enqueued = pc.Enqueued()
        self.busy = pc.Busy()
        self.driver = driver_class(self.enqueued, self.busy, self.name)
        self.exposed = self.driver.exposed
        self.recorded = self.driver.recorded
        self.initialized = self.driver.initialized
        self.offset = self.driver.offset
        self.current_position = self.exposed[0]
        self.gui = gui_class(self)  # TODO: more
        self.native_units = self.driver.native_units
        self.destination = pc.Number(units=self.native_units, display=True)
        self.destination.write(self.current_position.read(self.native_units), self.native_units)
        self.limits = self.driver.limits
        self.q = pc.Q(self.enqueued, self.busy, self.driver)
        # start thread
        self.driver.moveToThread(self.thread)
        self.thread.start()
        # connect to address object signals
        self.driver.update_ui.connect(self.update)
        self.driver.initialized_signal.connect(self.on_address_initialized)
        for obj in self.exposed:
            obj.updated.connect(self.update)
        self.busy.update_signal = self.driver.update_ui
        # initialize hardware
        self.q.push('initialize', driver_arguments)
        # integrate close into PyCMDS shutdown
        self.shutdown_timeout = 30  # seconds
        g.shutdown.add_method(self.close)
        g.hardware_waits.add(self.wait_until_still)
        hardwares.append(self)

    def close(self):
        # begin hardware shutdown
        self.q.push('close')
        # wait for hardware shutdown to complete
        start_time = time.time()
        self.q.push('check_busy')
        while self.busy.read():
            if time.time()-start_time < self.shutdown_timeout:
                self.busy.wait_for_update()
            else:
                g.logger.log('warning',
                             'Wait until done timed out',
                             self.name)
                break
        # quit thread
        self.thread.exit()
        self.thread.quit()

    def get_destination(self, output_units='same'):
        return self.destination.read(output_units=output_units)

    def get_position(self, output_units='same'):
        return self.current_position.read(output_units=output_units)

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
        self.q.push('set_position', [destination])

    @property
    def units(self):
        return self.current_position.units

    def update(self):
        self.update_ui.emit()

    def wait_until_still(self):
        while self.busy.read():
            self.busy.wait_for_update()

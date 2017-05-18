"""
Parent hardware class and associated.
"""


### import ####################################################################


import time

from PyQt4 import QtCore

import WrightTools as wt

import project.classes as pc 
import project.project_globals as g


### driver ####################################################################


class Driver(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    queue_emptied = QtCore.pyqtSignal()
    initialized_signal = QtCore.pyqtSignal()

    def __init__(self, hardware_obj, enqueued_obj, busy_obj, name, ctrl_class):
        QtCore.QObject.__init__(self)
        self.hardware = hardware_obj
        self.enqueued = enqueued_obj
        self.busy = busy_obj
        self.name = name
        self.ctrl = ctrl_class()
        self.exposed = self.ctrl.exposed
        self.recorded = self.ctrl.recorded
        self.initialized = self.ctrl.initialized
        self.offset = self.ctrl.offset
        ctrl_methods =  wt.kit.get_methods(self.ctrl)      
        for method in ctrl_methods:
            if hasattr(self, method):
                pass  # do not overwrite methods of address
            else:
                additional_method = getattr(self.ctrl, method)
                setattr(self, method, additional_method)
        self.gui = self.ctrl.gui
        self.native_units = self.ctrl.native_units
        self.limits = self.ctrl.limits

    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        '''
        accepts queued signals from 'queue' (address using q method) \n
        string method, list inputs
        '''
        self.update_ui.emit()
        if g.debug.read():
            print(self.name, 'dequeue:', method, inputs)
        # execute method
        getattr(self, str(method))(inputs)  # method passed as qstring
        # remove method from enqueued
        self.enqueued.pop()
        if not self.enqueued.read():
            self.queue_emptied.emit()
            self.check_busy([])
            self.update_ui.emit()

    def check_busy(self, inputs):
        '''
        decides if the hardware is done and handles writing of 'busy' to False
        '''
        # must always write busy whether answer is True or False
        if self.ctrl.is_busy():
            time.sleep(0.01)  # don't loop like crazy
            self.busy.write(True)
        elif self.enqueued.read():
            time.sleep(0.1)  # don't loop like crazy
            self.busy.write(True)
        else:
            self.busy.write(False)
            self.update_ui.emit()

    def get_position(self, inputs):
        self.ctrl.get_position()
        self.update_ui.emit()

    def poll(self, inputs):
        '''
        polling only gets enqueued by Hardware when not in module control
        '''
        self.get_position([])
        self.is_busy([])

    def initialize(self, inputs):
        self.ctrl.initialize(inputs, self)
        g.logger.log('info', self.name + ' Initializing', message=str(inputs))
        if g.debug.read():
            print(self.name, 'initialization complete')
            
    def set_offset(self, inputs):
        self.ctrl.set_offset(inputs[0])
        self.get_position([])

    def set_position(self, inputs):
        self.ctrl.set_position(inputs[0])
        self.get_position([])

    def close(self, inputs):
        self.ctrl.close()


### gui #######################################################################


class GUI:
    
    def __init__(self):
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

    def __init__(self, control_class, control_arguments, address_class=pc.Address,
                 name='', initialize_hardware=True, friendly_name=''):
        '''
        container for all objects relating to a single piece
        of addressable hardware
        '''
        QtCore.QObject.__init__(self)
        self.name = name
        self.friendly_name = friendly_name
        # create objects
        self.thread = QtCore.QThread()
        self.enqueued = pc.Enqueued()
        self.busy = pc.Busy()
        self.address = address_class(self, self.enqueued, self.busy,
                                     name, control_class)
        self.exposed = self.address.exposed
        self.recorded = self.address.recorded
        self.initialized = self.address.initialized
        self.offset = self.address.offset
        self.current_position = self.exposed[0]
        self.gui = self.address.gui
        self.native_units = self.address.native_units
        self.destination = pc.Number(units=self.native_units, display=True)
        self.destination.write(self.current_position.read(self.native_units), self.native_units)
        self.limits = self.address.limits
        self.q = pc.Q(self.enqueued, self.busy, self.address)
        # start thread
        self.address.moveToThread(self.thread)
        self.thread.start()
        # connect to address object signals
        self.address.update_ui.connect(self.update)
        self.address.initialized_signal.connect(self.on_address_initialized)
        for obj in self.exposed:
            obj.updated.connect(self.update)
        self.busy.update_signal = self.address.update_ui
        # initialize hardware
        self.q.push('initialize', control_arguments)
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

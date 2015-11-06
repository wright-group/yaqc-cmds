### import ####################################################################


import os
import time

import numpy as np

from PyQt4 import QtCore
from PyQt4 import QtGui

import project_globals as g

import WrightTools as wt
import WrightTools.units as wt_units


### mutex #####################################################################


class Mutex(QtCore.QMutex):
    
    def __init__(self, initial_value=None):
        QtCore.QMutex.__init__(self)
        self.WaitCondition = QtCore.QWaitCondition()
        self.value = initial_value
        
    def read(self):
        return self.value
        
    def write(self, value):
        self.lock()
        self.value = value
        self.WaitCondition.wakeAll()
        self.unlock()
        
    def wait_for_update(self, timeout=5000):
        if self.value:
            return self.WaitCondition.wait(self, msecs=timeout)

class Busy(QtCore.QMutex):

    def __init__(self):
        '''
        QMutex object to communicate between threads that need to wait \n
        while busy.read(): busy.wait_for_update()
        '''
        QtCore.QMutex.__init__(self)
        self.WaitCondition = QtCore.QWaitCondition()
        self.value = False
        self.type = 'busy'
        self.update_signal = None

    def read(self):
        return self.value

    def write(self, value):
        '''
        bool value
        '''
        self.tryLock(10)  # wait at most 10 ms before moving forward
        self.value = value
        self.unlock()
        self.WaitCondition.wakeAll()

    def wait_for_update(self, timeout=5000):
        '''
        wait in calling thread for any thread to call 'write' method \n
        int timeout in milliseconds
        '''
        if self.value:
            return self.WaitCondition.wait(self, msecs=timeout)


### gui items #################################################################


class Value(QtCore.QMutex):

    def __init__(self, initial_value=None):
        '''
        Basic QMutex object to hold a single object in a thread-safe way.
        '''
        QtCore.QMutex.__init__(self)
        self.value = initial_value

    def read(self):
        return self.value

    def write(self, value):
        self.lock()
        self.value = value
        self.unlock()


class PyCMDS_Object(QtCore.QObject):
    updated = QtCore.pyqtSignal()
    disabled = False

    def __init__(self, initial_value=None,
                 ini=None, section='', option='',
                 import_from_ini=False, save_to_ini_at_shutdown=False,
                 display=False, name='', label = '', set_method=None,
                 disable_under_module_control=False,
                 *args, **kwargs):
        QtCore.QObject.__init__(self)
        self.has_widget = False
        self.tool_tip = ''
        self.value = Value(initial_value)
        self.display = display
        self.set_method = set_method
        if self.display:
            self.disabled = True
        else:
            self.disabled = False
        # ini
        if ini:
            self.has_ini = True
            self.ini = ini
            self.section = section
            self.option = option
        else:
            self.has_ini = False
        if import_from_ini:
            self.get_saved()
        if save_to_ini_at_shutdown:
            g.shutdown.add_method(self.save)
        # name
        self.name = name
        if not label == '':
            pass
        else:
            self.label = self.name
        # disable under module control
        if disable_under_module_control:
            g.main_window.read().module_control.connect(self.on_module_control)
            
    def on_module_control(self):
        if g.module_control.read():
            if self.has_widget:
                self.widget.setDisabled(True)
        else:
            self.widget.setDisabled(self.disabled)

    def read(self):
        return self.value.read()

    def write(self, value):
        self.value.write(value)
        self.updated.emit()

    def get_saved(self):
        if self.has_ini:
            self.value.write(self.ini.read(self.section, self.option))
        self.updated.emit()

    def save(self, value=None):
        if value is not None:
            self.value.write(value)
        if self.has_ini:
            self.ini.write(self.section, self.option, self.value.read())

    def set_disabled(self, disabled):
        self.disabled = bool(disabled)
        if self.has_widget:
            self.widget.setDisabled(self.disabled)
            
    def setDisabled(self, disabled):
        self.set_disabled(disabled)
            
    def set_tool_tip(self, tool_tip):
        self.tool_tip = str(tool_tip)
        if self.has_widget:
            self.widget.setToolTip(self.tool_tip)


class Bool(PyCMDS_Object):
    '''
    holds 'value' (bool) - the state of the checkbox

    use read method to access
    '''

    def __init__(self, initial_value=False, *args, **kwargs):
        PyCMDS_Object.__init__(self, initial_value=initial_value,
                               *args, **kwargs)
        self.type = 'checkbox'
        
    def give_control(self, control_widget):
        self.widget = control_widget
        # set
        self.widget.setChecked(self.value.read())
        # connect signals and slots
        self.updated.connect(lambda: self.widget.setChecked(self.value.read()))
        self.widget.stateChanged.connect(lambda: self.write(self.widget.isChecked()))
        # finish
        self.widget.setToolTip(self.tool_tip)
        self.widget.setDisabled(self.disabled)
        self.has_widget = True


class Combo(PyCMDS_Object):

    def __init__(self, allowed_values=['None'], initial_value=None, *args, **kwargs):
        PyCMDS_Object.__init__(self, *args, **kwargs)
        self.type = 'combo'
        self.allowed_values = allowed_values
        self.data_type = type(allowed_values[0])
        if initial_value is None:
            self.write(self.allowed_values[0])

    def associate(self, display=None, pre_name=''):
        # display
        if display is None:
            display = self.display
        # name
        name = pre_name + self.name
        # new object
        new_obj = Combo(initial_value=self.read(), display=display,
                        allowed_values=self.allowed_values, name=name)
        return new_obj
        
    def read_index(self):
        return self.allowed_values.index(self.read())

    def save(self, value=None):
        if value is not None:
            self.value.write(value)
        if self.has_ini:
            self.ini.write(self.section, self.option, self.value.read(), with_apostrophe=True)
            
    def set_allowed_values(self, allowed_values):
        '''
        Set the allowed values of the Combo object. 
        
        Parameters
        ----------
        allowed_values : list
            the new allowed values
        
        Notes
        ----------
        The value of the object is written to the first allowed value if the
        current value is not in the allowed values.
        '''
        if allowed_values == self.allowed_values:
            return
        self.allowed_values = allowed_values
        # update widget
        if self.has_widget:
            self.widget.currentIndexChanged.disconnect(self.write_from_widget)
            self.widget.clear()
            allowed_values_strings = [str(value) for value in self.allowed_values]
            self.widget.addItems(allowed_values_strings)
            self.widget.currentIndexChanged.connect(self.write_from_widget)
        # write value again
        if self.read() not in self.allowed_values:
            self.write(self.allowed_values[0])
        else:
            self.write(self.read())
            
    def set_widget(self):
        allowed_values_strings = [str(value) for value in self.allowed_values]
        index = allowed_values_strings.index(str(self.read()))
        self.widget.setCurrentIndex(index)

    def write(self, value):
        # value will be maintained as original data type
        value = self.data_type(value)
        PyCMDS_Object.write(self, value)
        
    def write_from_widget(self):
        # needs to be defined method so we can connect and disconnect
        self.write(self.widget.currentText())

    def give_control(self, control_widget):
        self.widget = control_widget
        # fill out items
        allowed_values_strings = [str(value) for value in self.allowed_values]
        self.widget.addItems(allowed_values_strings)
        if self.read() is not None:
            self.widget.setCurrentIndex(allowed_values_strings.index(str(self.read())))       
        # connect signals and slots
        self.updated.connect(self.set_widget)
        self.widget.currentIndexChanged.connect(self.write_from_widget)
        self.widget.setToolTip(self.tool_tip)
        self.widget.setDisabled(self.disabled)
        self.has_widget = True


class Filepath(PyCMDS_Object):

    def __init__(self, caption='Open', directory=None, options=[],
                 *args, **kwargs):
        '''
        holds the filepath as a string \n
        '''
        PyCMDS_Object.__init__(self, *args, **kwargs)
        self.type = 'filepath'
        self.caption = caption
        self.directory = directory
        self.options = options
        
    def give_control(self, control_widget):
        self.widget = control_widget
        if self.read() is not None:
            self.widget.setText(self.read())
        # connect signals and slots
        self.updated.connect(lambda: self.widget.setText(self.read()))
        self.widget.setToolTip(str(self.read()))
        self.updated.connect(lambda: self.widget.setToolTip(self.read()))
        self.has_widget = True
        
    def give_button(self, button_widget):
        self.button = button_widget
        self.button.clicked.connect(self.on_load)
        
    def on_load(self):
        import file_dialog_handler
        # directory
        if self.directory is not None:
            directory_string = self.directory
        else:
            if self.read() is not None:    
                directory_string = self.read()
            else:
                directory_string = g.main_dir.read()
        # filter
        filter_string = ';;'.join(self.options + ['All Files (*.*)'])
        out = file_dialog_handler.open_dialog(self.caption, directory_string, filter_string)
        if os.path.isfile(out):
            self.write(out)


class NumberLimits(PyCMDS_Object):

    def __init__(self, min_value=-1000000., max_value=1000000., units=None):
        '''
        not appropriate for use as a gui element - only for backend use
        units must never change for this kind of object
        '''
        PyCMDS_Object.__init__(self)
        PyCMDS_Object.write(self, [min_value, max_value])
        self.units = units

    def read(self, output_units='same'):
        min_value, max_value = PyCMDS_Object.read(self)
        if output_units == 'same':
            pass
        else:
            min_value = wt_units.converter(min_value, self.units, output_units)
            max_value = wt_units.converter(max_value, self.units, output_units)
        # ensure order
        min_value, max_value = [min([min_value, max_value]),
                                max([min_value, max_value])]
        return [min_value, max_value]

    def write(self, min_value, max_value, input_units='same'):
        if input_units == 'same':
            pass
        else:
            min_value = wt_units.converter(min_value, input_units, self.units)
            max_value = wt_units.converter(max_value, input_units, self.units)
        # ensure order
        min_value, max_value = [min([min_value, max_value]),
                                max([min_value, max_value])]
        PyCMDS_Object.write(self, [min_value, max_value])
        self.updated.emit()


class Number(PyCMDS_Object):

    def __init__(self, initial_value=np.nan, single_step=1., decimals=3, 
                 limits=NumberLimits(), units=None, *args, **kwargs):
        PyCMDS_Object.__init__(self, initial_value=initial_value,
                               *args, **kwargs)
        self.type = 'number'
        self.disabled_units = False
        self.single_step = single_step
        self.decimals = decimals
        self.set_control_steps(single_step, decimals)
        # units
        self.units = units
        self.units_kind = None
        for dic in wt_units.unit_dicts:
            if self.units in dic.keys():
                self.units_dic = dic
                self.units_kind = dic['kind']
        # limits
        self.limits = limits
        if self.units is None:
            self.limits.units = None
        if self.units is not None and self.limits.units is None:
            self.limits.units = self.units
        self._set_limits()
        self.limits.updated.connect(lambda: self._set_limits())

    def associate(self, display=None, pre_name=''):
        # display
        if display is None:
            display = self.display
        # name
        name = pre_name + self.name
        # new object
        new_obj = Number(initial_value=self.read(), display=display,
                         units=self.units, limits=self.limits,
                         single_step=self.single_step,
                         decimals=self.decimals, name=name)
        return new_obj

    def convert(self, destination_units):
        # value
        old_val = self.value.read()
        new_val = wt_units.converter(old_val, self.units, str(destination_units))
        self.value.write(new_val)
        # commit and signal
        self.units = str(destination_units)
        self._set_limits()
        self.updated.emit()

    def read(self, output_units='same'):
        value = PyCMDS_Object.read(self)
        if output_units == 'same':
            pass
        else:
            value = wt_units.converter(value, self.units, output_units)
        return value

    def set_control_steps(self, single_step=None, decimals=None):
        limits = [self.single_step, self.decimals]
        inputs = [single_step, decimals]
        widget_methods = ['setSingleStep', 'setDecimals']
        for i in range(len(limits)):
                if not inputs[i] is None:
                    limits[i] = inputs[i]
                if self.has_widget:
                    getattr(self.widget, widget_methods[i])(limits[i])
                    
    def set_disabled_units(self, disabled):
        self.disabled_units = bool(disabled)
        if self.has_widget:
            self.units_widget.setDisabled(self.disabled_units)

    def set_widget(self):
        # special value text is displayed when widget is at minimum
        if np.isnan(self.value.read()):
            self.widget.setSpecialValueText('nan')
            self.widget.setValue(self.widget.minimum())
        else:
            self.widget.setSpecialValueText('')
            self.widget.setValue(self.value.read())

    def give_control(self, control_widget):
        self.widget = control_widget
        # set values
        min_value, max_value = self.limits.read()
        self.widget.setMinimum(min_value)
        self.widget.setMaximum(max_value)
        self.widget.setDecimals(self.decimals)
        self.widget.setSingleStep(self.single_step)
        self.set_widget()
        # connect signals and slots
        self.updated.connect(self.set_widget)
        self.widget.editingFinished.connect(lambda: self.write(self.widget.value()))
        # finish
        self.widget.setToolTip(self.tool_tip)
        self.widget.setDisabled(self.disabled)
        self.has_widget = True

    def give_units_combo(self, units_combo_widget):
        self.units_widget = units_combo_widget
        # add items
        unit_types = self.units_dic.keys()
        unit_types.remove('kind')
        self.units_widget.addItems(unit_types)
        # set current item
        self.units_widget.setCurrentIndex(unit_types.index(self.units))
        # associate update with conversion
        self.units_widget.currentIndexChanged.connect(lambda: self.convert(self.units_widget.currentText()))
        # finish
        self.units_widget.setDisabled(self.disabled_units)

    def write(self, value, input_units='same'):
        if input_units == 'same':
            pass
        else:
            value = wt_units.converter(value, input_units, self.units)
        PyCMDS_Object.write(self, value)

    def _set_limits(self):
        min_value, max_value = self.limits.read()
        limits_units = self.limits.units
        min_value = wt_units.converter(min_value, limits_units, self.units)
        max_value = wt_units.converter(max_value, limits_units, self.units)
        # ensure order
        min_value, max_value = [min([min_value, max_value]),
                                max([min_value, max_value])]
        if self.has_widget:
            self.widget.setMinimum(min_value)
            self.widget.setMaximum(max_value)
        if not self.display:
            self.set_tool_tip('min: ' + str(min_value) + '\n' +
                              'max: ' + str(max_value))


class String(PyCMDS_Object):

    def __init__(self, initial_value='', *args, **kwargs):
        PyCMDS_Object.__init__(self, initial_value=initial_value, *args, **kwargs)
        self.type = 'string'

    def give_control(self, control_widget):
        self.widget = control_widget
        # fill out items
        self.widget.setText(str(self.value.read()))
        # connect signals and slots
        self.updated.connect(lambda: self.widget.setText(self.value.read()))
        self.widget.editingFinished.connect(lambda: self.write(self.widget.text()))
        self.widget.setToolTip(self.tool_tip)
        self.has_widget = True
            
    def read(self):
        return str(PyCMDS_Object.read(self))


### hardware ##################################################################


class Address(QtCore.QObject):
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
            print self.name, 'dequeue:', method, inputs
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
            print self.name, 'initialization complete'
            
    def set_offset(self, inputs):
        self.ctrl.set_offset(inputs[0])
        self.get_position([])

    def set_position(self, inputs):
        self.ctrl.set_position(inputs[0])
        self.get_position([])

    def close(self, inputs):
        self.ctrl.close()


class Enqueued(QtCore.QMutex):

    def __init__(self):
        '''
        holds list of enqueued options
        '''
        QtCore.QMutex.__init__(self)
        self.value = []

    def read(self):
        return self.value

    def push(self, value):
        self.lock()
        self.value.append(value)
        self.unlock()

    def pop(self):
        self.lock()
        self.value = self.value[1:]
        self.unlock()


class Q:

    def __init__(self, enqueued, busy, address):
        self.enqueued = enqueued
        self.busy = busy
        self.address = address
        self.queue = QtCore.QMetaObject()

    def push(self, method, inputs=[]):
        self.enqueued.push([method, time.time()])
        self.busy.write(True)
        # send Qt SIGNAL to address thread
        self.queue.invokeMethod(self.address,
                                'dequeue',
                                QtCore.Qt.QueuedConnection,
                                QtCore.Q_ARG(str, method),
                                QtCore.Q_ARG(list, inputs))


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

    def __init__(self, control_class, control_arguments, address_class=Address,
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
        self.enqueued = Enqueued()
        self.busy = Busy()
        self.address = address_class(self, self.enqueued, self.busy,
                                     name, control_class)
        self.exposed = self.address.exposed
        self.recorded = self.address.recorded
        self.initialized = self.address.initialized
        self.offset = self.address.offset
        self.current_position = self.exposed[0]
        self.gui = self.address.gui
        self.native_units = self.address.native_units
        self.destination = Number(units=self.native_units, display=True)
        self.destination.write(self.current_position.read(self.native_units), self.native_units)
        self.limits = self.address.limits
        self.q = Q(self.enqueued, self.busy, self.address)
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

    def get_position(self):
        return self.current_position.read()

    def is_valid(self, destination, input_units=None):
        if input_units is None:
            pass
        else:
            destination = wt_units.converter(destination,
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

    def poll(self, force=False):
        if force:
            self.q.push('poll')
            self.get_position()
        elif not g.module_control.read():
            self.q.push('poll')
            self.get_position()
            
    def set_offset(self, offset, input_units=None):
        if input_units is None:
            pass
        else:
            offset = wt_units.converter(offset,
                                        input_units,
                                        self.native_units)
        self.q.push('set_offset', [offset])

    def set_position(self, destination, input_units=None):
        if input_units is None:
            pass
        else:
            destination = wt_units.converter(destination,
                                             input_units,
                                             self.native_units)
        self.destination.write(destination, self.native_units)
        self.q.push('set_position', [destination])

    def update(self):
        self.update_ui.emit()

    def wait_until_still(self):
        while self.busy.read():
            self.busy.wait_for_update()

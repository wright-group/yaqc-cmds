### import #####################################################################

import time

import numpy as np

from PyQt4 import QtGui, QtCore

import project_globals as g

import ini_handler as ini

### gui items ##################################################################

# These are a special group of classes that are specifically designed to work
# seamlessly in the context of the gui. They are divided by datatype. Each class
# has a corresponding method in the custom_widgets/input_table class.

# These classes are not meant to be used for commonly updated items such as DAQ
# readings - they are not mutex.

# Each class has a signal 'updated' and a method 'set_disabled'.

class gui_object(QtCore.QObject):
    '''
    holds 'value' (bool) - the state of the checkbox
    
    use read method to access
    '''
    updated = QtCore.pyqtSignal()
    disabled = False
    def __init__(self, initial_value = None, ini_inputs = None, import_from_ini = False, save_to_ini_at_shutdown = False):
        '''
        list ini inputs [ini object, str section, str option]
        '''
        QtCore.QObject.__init__(self)
        self.type = 'checkbox'
        self.has_widget = False
        self.tool_tip = ''
        self.value = initial_value
        #ini
        if ini_inputs:
            self.has_ini = True
            self.ini = ini_inputs[0]
            self.section = ini_inputs[1]
            self.option = ini_inputs[2]
        else:
            self.has_ini = False
        if import_from_ini: 
            self.get_saved()
        if save_to_ini_at_shutdown: 
            g.shutdown.add_method(self.save)
    def read(self):
        return self.value
    def write(self, value):  
        self.value = value
        self.updated.emit()
    def get_saved(self):
        if self.has_ini:
            self.value = self.ini.read(self.section, self.option)
        return self.value
        self.updated.emit()
    def save(self, value = None):
        if not value == None: 
            self.value = value
        if self.has_ini:
            self.ini.write(self.section, self.option, self.value)
    def set_disabled(self, disabled):
        self.disabled = disabled
        if self.has_widget: self.widget.setDisabled(self.disabled)
    def set_tool_tip(self, tool_tip):
        self.tool_tip = tool_tip
        if self.has_widget: self.widget.setToolTip(self.tool_tip)
    def give_control(self, control_widget):
        self.widget = control_widget
        #set
        self.widget.setChecked(self.value)   
        #connect signals and slots
        self.updated.connect(lambda: self.widget.setChecked(self.value))
        self.widget.stateChanged.connect(lambda: self.write(self.widget.checkState()))
        #finish
        self.widget.setToolTip(self.tool_tip)
        self.widget.setDisabled(self.disabled)
        self.has_widget = True

class boolean(gui_object):
    '''
    holds 'value' (bool) - the state of the checkbox
    
    use read method to access
    '''
    def __init__(self, initial_value = None, ini = None, import_from_ini = False, save_to_ini_at_shutdown = False):
        gui_object.__init__(self, initial_value = initial_value, ini_inputs = ini, import_from_ini = import_from_ini, save_to_ini_at_shutdown = save_to_ini_at_shutdown)
    def give_control(self, control_widget):
        self.widget = control_widget
        #set
        self.widget.setChecked(self.value)   
        #connect signals and slots
        self.updated.connect(lambda: self.widget.setChecked(self.value))
        self.widget.stateChanged.connect(lambda: self.write(self.widget.checkState()))
        #finish
        self.widget.setToolTip(self.tool_tip)
        self.widget.setDisabled(self.disabled)
        self.has_widget = True

class combo(gui_object):
    '''
    holds 'value' (str) - the combobox displayed text
    
    holds 'allowed_values' (list of str)
    '''
    updated = QtCore.pyqtSignal()
    disabled = False
    def __init__(self, allowed_values, initial_value = None, ini = None, import_from_ini = False, save_to_ini_at_shutdown = False):
        gui_object.__init__(self, initial_value = initial_value, ini_inputs = ini, import_from_ini = import_from_ini, save_to_ini_at_shutdown = save_to_ini_at_shutdown)
        self.allowed_values = allowed_values
    def give_control(self, control_widget):
        self.widget = control_widget
        #fill out items
        self.widget.addItems(self.allowed_values)
        self.widget.setCurrentIndex(self.allowed_values.index(self.read()))       
        #connect signals and slots
        self.updated.connect(lambda: self.widget.setCurrentIndex(self.allowed_values.index(self.read())))
        self.widget.currentIndexChanged.connect(lambda: self.write(self.widget.currentText()))
        self.widget.setToolTip(self.tool_tip)
        self.widget.setDisabled(self.disabled)
        self.has_widget = True

class filepath(gui_object):
    '''
    holds 'value' (str) - the filepath as a string
    '''
    def __init__(self, initial_value = None, ini = None, import_from_ini = False, save_to_ini_at_shutdown = False):
        gui_object.__init__(self, initial_value = initial_value, ini_inputs = ini, import_from_ini = import_from_ini, save_to_ini_at_shutdown = save_to_ini_at_shutdown)
    def give_control(self, control_widget):
        self.widget = control_widget
        '''
        #fill out items
        self.widget.addItems(self.allowed_values)
        self.widget.setCurrentIndex(self.allowed_values.index(self.read()))       
        #connect signals and slots
        self.updated.connect(lambda: self.widget.setCurrentIndex(self.allowed_values.index(self.read())))
        self.widget.currentIndexChanged.connect(lambda: self.write(self.widget.currentText()))
        '''
        self.widget.setToolTip(self.tool_tip)
        self.widget.setDisabled(self.disabled)
        self.has_widget = True
    def give_button(self, button_widget):
        self.button = button_widget
            
class number(QtCore.QObject):
    '''
    holds 'value' (float 64)
    
    units_kind one in ['color', 'delay', None (default)]
    
    native units: nm (color), fs (delay). values are written to ini in native
    units. if you supply an inital_value it must be in native units.
    '''
    updated = QtCore.pyqtSignal()
    disabled = False
    def __init__(self, 
                 initial_value = None, 
                 display = False, 
                 ini = None, 
                 import_from_ini = False, 
                 save_to_ini_at_shutdown = False, 
                 units_kind = None, 
                 min_value = -1000000., 
                 max_value = 1000000.,
                 single_step = 1.,
                 decimals = 2):
        QtCore.QObject.__init__(self)
        self.type = 'number'
        self.has_widget = False
        self.tool_tip = ''
        self.display = display
        self.units_kind = units_kind
        self.ini_inputs = ini
        self.value = initial_value
        self.min_value = min_value
        self.max_value = max_value
        self.single_step = single_step
        self.decimals = decimals
        if import_from_ini: self.get_saved()
        if save_to_ini_at_shutdown: g.shutdown.add_method(self.save)
    def read(self):
        return self.value
    def write(self, value):
        self.value = float(value)
        self.updated.emit()
    def get_saved(self):
        self.value = self.ini_inputs[0].read(self.ini_inputs[1], self.ini_inputs[2])
        return self.value
        self.updated.emit()
    def save(self, value = None):
        if not value == None: self.value = value
        self.ini_inputs[0].write(self.ini_inputs[1], self.ini_inputs[2], self.value)
    def set_disabled(self, disabled):
        self.disabled = disabled
        if self.has_widget: self.widget.setDisabled(self.disabled)
    def set_tool_tip(self, tool_tip):
        self.tool_tip = tool_tip
        if self.has_widget: self.widget.setToolTip(self.tool_tip)
    def set_limits(self, min_value = None, max_value = None, single_step =   None, decimals = None):
        limits = [self.min_value, self.max_value, self.single_step, self.decimals]
        inputs = [min_value, max_value, single_step, decimals]
        widget_methods = ['setMinimum', 'setMaximum', 'setSingleStep', 'setDecimals']
        for i in range(len(limits)):
            if not inputs[i] == None:
                limits[i] = inputs[i]
                if self.has_widget: getattr(self.widget, widget_methods[i])(limits[i])                
    def give_control(self, control_widget):
        self.widget = control_widget
        #set values        
        self.widget.setDecimals(self.decimals)
        self.widget.setMaximum(self.max_value)
        self.widget.setMinimum(self.min_value)
        self.widget.setSingleStep(self.single_step)
        self.widget.setValue(self.value)
        #connect signals and slots
        self.updated.connect(lambda: self.widget.setValue(self.value))
        self.widget.editingFinished.connect(lambda: self.write(self.widget.value()))
        #finish
        self.widget.setToolTip(self.tool_tip)
        self.has_widget = True
    def give_units_combo(self, units_combo_widget):
        self.units_widget = units_combo_widget
        if self.units_kind == 'color':
            self.units_widget.addItems(['nm', 'wn', 'eV'])
        elif self.units_kind == 'delay':
            self.units_widget.addItems(['fs', 'ps'])
            
class string(gui_object):
    '''
    holds 'value' (string)
    '''
    def __init__(self, initial_value = None, ini = None, import_from_ini = False, save_to_ini_at_shutdown = False):
        gui_object.__init__(self, initial_value = initial_value, ini_inputs = ini, import_from_ini = import_from_ini, save_to_ini_at_shutdown = save_to_ini_at_shutdown)
    def give_control(self, control_widget):
        self.widget = control_widget
        #fill out items
        self.widget.setText(self.value)       
        #connect signals and slots
        self.updated.connect(lambda: self.widget.setText(self.value))
        self.widget.editingFinished.connect(lambda: self.write(self.widget.text()))
        self.widget.setToolTip(self.tool_tip)
        self.has_widget = True    
    
### hardware ###################################################################

class busy(QtCore.QMutex):
    def __init__(self):
        QtCore.QMutex.__init__(self)
        self.WaitCondition = QtCore.QWaitCondition()
        self.value = False
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
        
class address(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    queue_emptied = QtCore.pyqtSignal()
    
    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        '''
        accepts queued signals from 'queue' (address using q method)
        method must be string, inputs must be list
        '''
        #DO NOT CHANGE THIS METHOD UNLESS YOU ~REALLY~ KNOW WHAT YOU ARE DOING!
        self.update_ui.emit()
        if g.debug.read(): print 'mono dequeue:', method, inputs
        getattr(self, str(method))(inputs) #method passed as qstring
        enqueued_actions.pop()
        if not enqueued_actions.read(): 
            self.queue_emptied.emit()
            self.update_ui.emit()
            self.check_busy([])
            
    def check_busy(self, inputs):
        '''
        decides if the hardware is done and handles writing of 'busy' to False
        must always write busy whether answer is True or False
        should include a sleep if answer is True to prevent very fast loops: time.sleep(0.1)
        '''
        if enqueued_actions.read():
            time.sleep(0.1)
            busy.write(True)
        else:
            busy.write(False)
    
    def poll(self, inputs):
        '''
        what happens when the poll timer fires
        '''
        print 'opas poll'
            
    def initialize(self, inputs):
        if g.debug.read(): print 'MicroHR initializing'
        g.logger.log('info', 'MicroHR initializing')
        #current_position.write(destination.read())
        current_grating.write(grating_destination.read())
        current_color.write(color_destination.read())
    
    def go_to(self, inputs):
        ''' 
        go to value in inputs
        '''
        self.destination = inputs[0]
        time.sleep(1)
        current_position.write(self.destination)
        g.logger.log('debug', 'go_to', 'MicroHR sent to {}'.format(destination))
        self.update_ui.emit()
        print 'go_to done'
                      
    def shutdown(self, inputs):
         #cleanly shut down
         #all hardware classes must have this
         pass

class enqueued(QtCore.QMutex):
    def __init__(self):
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

class q:
    def __init__(self, busy_object, enqueued_actions_object, address_object):
        self.busy = busy_object
        self.enqueued = enqueued()
        self.address = address_object
    def push(self, method, inputs = []):
        #add to friendly queue list 
        self.enqueued.push([method, time.time()])
        #busy
        if not self.busy.read(): 
            self.busy.write(True)
        #send Qt SIGNAL to address thread
        queue.invokeMethod(self.address, 'dequeue', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, method), QtCore.Q_ARG(list, inputs))

### misc #######################################################################


    

    
    
    
    
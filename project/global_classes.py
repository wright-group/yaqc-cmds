### import######################################################################

import numpy as np

from PyQt4 import QtGui, QtCore

import project_globals as g

import project.ini_handler as ini

### classes#####################################################################

#These are a special group of classes that are specifically designed to work
#seamlessly in the context of the gui. They are divided by datatype. Each class
#has a corresponding method in the custom_widgets/input_table class.

#These classes are not meant to be used for commonly updated items such as DAQ
#readings - they are not mutex.

#Each class has a signal 'updated' and a method 'set_disabled'.

class boolean(QtCore.QObject):
    '''
    holds 'value' (bool) - the state of the checkbox
    
    use read method to access
    '''
    updated = QtCore.pyqtSignal()
    disabled = False
    def __init__(self, initial_value = False, ini = None, import_from_ini = False, save_to_ini_at_shutdown = False):
        QtCore.QObject.__init__(self)
        self.type = 'checkbox'
        self.has_widget = False
        self.tool_tip = ''
        self.ini_inputs = ini
        self.value = initial_value
        if import_from_ini: self.get_saved()
        if save_to_ini_at_shutdown: g.shutdown.add_method(self.save)
    def read(self):
        return self.value
    def write(self, value):  
        self.value = value
        self.updated.emit()
    def get_saved(self):
        self.value = ini.read(self.ini_inputs[0], self.ini_inputs[1], self.ini_inputs[2])
        return self.value
        self.updated.emit()
    def save(self, value = None):
        if not value == None: self.value = value
        ini.write(self.ini_inputs[0], self.ini_inputs[1], self.ini_inputs[2], self.value)
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

class combo(QtCore.QObject):
    '''
    holds 'value' (str) - the combobox displayed text
    
    holds 'allowed_values' (list of str)
    '''
    updated = QtCore.pyqtSignal()
    disabled = False
    def __init__(self, allowed_values, initial_value = None, ini = None, import_from_ini = False, save_to_ini_at_shutdown = False):
        QtCore.QObject.__init__(self)
        self.type = 'combo'
        self.has_widget = False
        self.tool_tip = ''
        self.ini_inputs = ini
        self.allowed_values = allowed_values
        self.value = initial_value
        if import_from_ini: self.get_saved()
        if save_to_ini_at_shutdown: g.shutdown.add_method(self.save)
    def read(self):
        return self.value
    def write(self, value):  
        self.value = str(value)
        self.updated.emit()
    def get_saved(self):
        self.value = ini.read(self.ini_inputs[0], self.ini_inputs[1], self.ini_inputs[2])
        return self.value
        self.updated.emit()
    def save(self, value = None):
        if not value == None: self.value = value
        ini.write(self.ini_inputs[0], self.ini_inputs[1], self.ini_inputs[2], self.value, with_apostrophe = True)
    def set_disabled(self, disabled):
        self.disabled = disabled
        if self.has_widget: self.widget.setDisabled(self.disabled)
    def set_tool_tip(self, tool_tip):
        self.tool_tip = tool_tip
        if self.has_widget: self.widget.setToolTip(self.tool_tip)
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

class filepath(QtCore.QObject):
    '''
    holds 'value' (str) - the filepath as a string
    '''
    updated = QtCore.pyqtSignal()
    disabled = False
    def __init__(self, initial_value = None, ini = None, import_from_ini = False, save_to_ini_at_shutdown = False):
        QtCore.QObject.__init__(self)
        self.type = 'filepath'
        self.has_widget = False
        self.tool_tip = ''
        self.ini_inputs = ini
        self.value = initial_value
        if import_from_ini: self.get_saved()
        if save_to_ini_at_shutdown: g.shutdown.add_method(self.save)
    def read(self):
        return self.value
    def write(self, value):  
        self.value = str(value)
        self.updated.emit()
    def get_saved(self):
        self.value = ini.read(self.ini_inputs[0], self.ini_inputs[1], self.ini_inputs[2])
        return self.value
        self.updated.emit()
    def save(self, value = None):
        if not value == None: self.value = value
        ini.write(self.ini_inputs[0], self.ini_inputs[1], self.ini_inputs[2], self.value)
    def set_disabled(self, disabled):
        self.disabled = disabled
        if self.has_widget: self.widget.setDisabled(self.disabled)
    def set_tool_tip(self, tool_tip):
        self.tool_tip = tool_tip
        if self.has_widget: self.widget.setToolTip(self.tool_tip)
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
        self.value = ini.read(self.ini_inputs[0], self.ini_inputs[1], self.ini_inputs[2])
        return self.value
        self.updated.emit()
    def save(self, value = None):
        if not value == None: self.value = value
        ini.write(self.ini_inputs[0], self.ini_inputs[1], self.ini_inputs[2], self.value)
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
            
class string(QtCore.QObject):
    '''
    holds 'value' (string)
    '''
    updated = QtCore.pyqtSignal()
    disabled = False
    def __init__(self, initial_value = None, display = False, ini = None, import_from_ini = False, save_to_ini_at_shutdown = False):
        QtCore.QObject.__init__(self)
        self.type = 'string'
        self.has_widget = False
        self.tool_tip = ''
        self.display = display
        self.ini_inputs = ini
        self.value = initial_value
        if import_from_ini: self.get_saved()
        if save_to_ini_at_shutdown: g.shutdown.add_method(self.save)
    def read(self):
        return self.value
    def write(self, value):  
        self.value = str(value)
        self.updated.emit()
    def get_saved(self):
        self.value = ini.read(self.ini_inputs[0], self.ini_inputs[1], self.ini_inputs[2])
        return self.value
        self.updated.emit()
    def save(self, value = None):
        if not value == None: self.value = value
        ini.write(self.ini_inputs[0], self.ini_inputs[1], self.ini_inputs[2], self.value, with_apostrophe = True)
    def set_disabled(self, disabled):
        self.disabled = disabled
        if self.has_widget: self.widget.setDisabled(self.disabled)
    def set_tool_tip(self, tool_tip):
        self.tool_tip = tool_tip
        if self.has_widget: self.widget.setToolTip(self.tool_tip)
    def give_control(self, control_widget):
        self.widget = control_widget
        #fill out items
        self.widget.setText(self.value)       
        #connect signals and slots
        self.updated.connect(lambda: self.widget.setText(self.value))
        self.widget.editingFinished.connect(lambda: self.write(self.widget.text()))
        self.widget.setToolTip(self.tool_tip)
        self.has_widget = True    
    
    
    
    

    
    
    
    
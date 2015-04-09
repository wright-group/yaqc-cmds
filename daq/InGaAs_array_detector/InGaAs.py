#to do##########################################################################

#[ ] create array tab gui here (that way it is seperate for each detection type)
#[ ] hand daq the relevant parameters for daq settings gui
#[ ] respond to daq calls in a defined way (shared between any possible array)
#[ ] calculate map
#  [ ] give settings for map parameters on array gui
#[ ] gui
#  [ ] display
#  [ ] settings
#[ ] handler for .ini file

### import######################################################################

import sys
import time

import numpy as np

from PyQt4 import QtCore, QtGui

import project.project_globals as g
app = g.app.read()
import project.custom_widgets as custom_widgets

import packages.serial as serial

### globals#####################################################################

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
        if self.value: return self.WaitCondition.wait(self, msecs=timeout)
busy = busy()

class enqueued_actions(QtCore.QMutex):
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
enqueued_actions = enqueued_actions()

class data(QtCore.QMutex):
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
        if self.value: return self.WaitCondition.wait(self, msecs=timeout)
data = data()

class data_map(QtCore.QMutex):
    def __init__(self):
        QtCore.QMutex.__init__(self)
        self.value = []
    def read(self):
        return self.value
    def write(self, value):
        self.lock()
        self.value = value
        self.WaitCondition.wakeAll()
        self.unlock()
data_map = data_map()

### address#####################################################################

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
        if g.debug.read(): print 'InGaAs dequeue:', method, inputs
        getattr(self, str(method))(inputs) #method passed as qstring
        enqueued_actions.pop()
        if not enqueued_actions.read(): 
            self.queue_emptied.emit()
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
            
    def initialize(self, inputs):
        if g.debug.read(): print 'InGaAs initializing'
        g.logger.log('info', 'InGaAs initializing')
    
        #initialize serial port-------------------------------------------------        
        
        self.serial_port = serial.Serial()
        self.serial_port.baudrate = 9600
        self.serial_port.port = 'COM8'
        
        #initialize arrays for later use----------------------------------------
        
        self.out = np.zeros(256)
        
        self.read([])
    
    def read(self, inputs):
        
        #get data as string from arduino----------------------------------------
        
        self.serial_port.open()
        self.serial_port.write('S')
        raw_string = self.serial_port.readline()
        self.serial_port.close()

        #process data-----------------------------------------------------------
        
        #remove 'ready' from end
        string = raw_string[:512]
        #encode to hex
        vals = np.array([elem.encode("hex") for elem in string])
        #reshape
        vals = vals.reshape(256, -1)
        vals = np.flipud(vals)
        #transform to floats
        for i in range(len(vals)):
            raw_pixel = int('0x' + vals[i, 0] + vals[i, 1], 16)
            pixel = 0.00195*(raw_pixel - (2060. + -0.0142*i)) 
            self.out[i] = pixel
            
        #finish-----------------------------------------------------------------
            
        data.write(self.out)
        self.update_ui.emit()
                      
    def shutdown(self, inputs):
        '''
        cleanly shut down
        
        all hardware address objects must have this, even if trivial
        '''
        if self.serial_port.isOpen():
            self.serial_port.close()

#begin address object in seperate thread
address_thread = QtCore.QThread()
address_obj = address()
address_obj.moveToThread(address_thread)
address_thread.start()

#create queue to communiate with address thread
queue = QtCore.QMetaObject()
def q(method, inputs = []):
    #add to friendly queue list 
    enqueued_actions.push([method, time.time()])
    #busy
    if not busy.read(): busy.write(True)
    #send Qt SIGNAL to address thread
    queue.invokeMethod(address_obj, 'dequeue', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, method), QtCore.Q_ARG(list, inputs))
    
### control#####################################################################

class control():
    
    def __init__(self):
        self.ready = False
        print 'control.__init__'
        g.shutdown.read().connect(self.shutdown)
        self.initialize_hardware()
        
    def initialize_hardware(self):
        q('initialize')
        
    def calculate_map(self, mono_setpoint = None):
        '''
        every array must have a this method
        
        depending on your array you may use inputs or not
        '''
        pass
        
    def read(self):
        '''
        every array must have a this method
        '''
        q('read')
    
    def wait_until_done(self, timeout = 10):
        '''
        timeout in seconds
        
        will only refer to timeout when busy.wait_for_update fires
        
        every array must have a this method
        '''
        start_time = time.time()
        while busy.read():
            if time.time()-start_time < timeout:
                if not enqueued_actions.read(): q('check_busy')
                busy.wait_for_update()
            else: 
                g.logger.log('warning', 'wait until done timed out', 'timeout set to {} seconds'.format(timeout))
                break
                
    def shutdown(self):
        '''
        every array must have a this method
        '''
        if g.debug.read(): print 'InGaAs shutting down'
        g.logger.log('info', 'InGaAs shutdown')
        q('shutdown')
        self.wait_until_done()
        address_thread.quit()
        gui.stop()
        
control = control()

### gui#########################################################################

class widget(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        '''
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        layout.setMargin(0)
        inputs = [[['Array'], 'heading', None, [None]]]
        input_table = custom_widgets.input_table(inputs)
        layout.addWidget(input_table)
        '''
        
class gui(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)
        address_obj.update_ui.connect(self.update)
        self.create_frame()
        
    def create_frame(self):
        
        #get parent widget------------------------------------------------------
        
        parent_widget = g.daq_array_widget.read()
        parent_widget.setLayout(QtGui.QHBoxLayout())
        #parent_widget.layout().setContentsMargins(0, 5, 0, 0)
        layout = parent_widget.layout()
        
        #display area-----------------------------------------------------------

        #container widget
        display_container_widget = QtGui.QWidget()
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)
        
        #big number
        self.big_display = custom_widgets.spinbox_as_display(font_size = 100)
        display_layout.addWidget(self.big_display)
        
        #plot
        self.plot_widget = custom_widgets.plot_1D()
        self.plot_curve = self.plot_widget.add_curve()
        self.plot_widget.set_labels(ylabel = 'arbitrary units')
        self.plot_line = self.plot_widget.add_line(color = 'y')  
        display_layout.addWidget(self.plot_widget)
        
        #streach
        spacer = custom_widgets.vertical_spacer()
        spacer.add_to_layout(display_layout)
        
        #vertical line----------------------------------------------------------

        line = custom_widgets.line('V')      
        layout.addWidget(line)
        
        #settings area----------------------------------------------------------
        
        #container widget / scroll area
        settings_container_widget = QtGui.QWidget()
        settings_scroll_area = custom_widgets.scroll_area()
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        layout.addWidget(settings_scroll_area)
        
        #array widget
        array_widget = widget()
        settings_layout.addWidget(array_widget)
        
        #input table
        '''
        inputs = [[['Graph & Big #'], 'heading', None, [None]],
                  [['Channel'], 'combo', tab_channel, [None]],
                  [['Property'], 'combo', tab_property, [None]],
                  [['Analog'], 'heading', None, [None]],
                  [['vai0 assignment', 'vai1 assignment', 'vai2 assignment', 'vai3 assignment', 'vai4 assignment'], 'number', analog_physical_channels, [[0, 10, 0, 1], [0, 10, 0, 1], [0, 10, 0, 1], [0, 10, 0, 1], [0, 10, 0, 1]]],
                  [['Minimum', 'Maximum'], 'number', analog_limits, [[-40, 40, 4, 0.1], [-40, 40, 4, 0.1]]],
                  [['Digital'], 'heading', None, [None]],
                  [['vdi0 assignment'], 'number', digital_physical_channels, [[0, 10, 0, 1]]],
                  [['Minimum', 'Maximum', 'Cutoff'], 'number', digital_limits, [[-40, 40, 4, 0.1], [-40, 40, 4, 0.1], [-40, 40, 4, 0.1]]]]
        input_table = custom_widgets.input_table(inputs)
        settings_layout.addWidget(input_table)
        '''
        
        #streach
        settings_layout.addStretch(1)
    
    def update(self):
        
        #import globals locally-------------------------------------------------
        
        #...
                
        if not data.read() == None:
            local_data = data.read()
            
            #plot-------------------------------------------------------------------

            x = np.linspace(0, len(local_data), len(local_data))           
            in_data = np.array([x, local_data])
            self.plot_curve.clear()
            self.plot_curve.setData(in_data[0], in_data[1])
            
            #data readout-----------------------------------------------------------

            self.big_display.setValue(local_data[100])
              
    def stop(self):
        pass
        
gui = gui()
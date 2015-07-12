### import######################################################################

import sys
import time

import numpy as np

from PyQt4 import QtCore, QtGui

import project.project_globals as g
app = g.app.read()
import project.custom_widgets as custom_widgets
import project.ini_handler as ini

### special globals ############################################################

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

class truing_enabled(QtCore.QObject):
    updated = QtCore.pyqtSignal()
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.get_saved()
    def read(self):
        return self.value
    def write(self, value):
        self.value = int(value)
        self.updated.emit()
    def get_saved(self):
        self.value = ini.read('spectrometers', 'Spec', 'truing enabled')
        return self.value
        self.updated.emit()
    def save(self, value = None):
        if not value == None: self.value = value
        ini.write('spectrometers', 'Spec', 'truing enabled', self.value)       
truing_enabled = truing_enabled()

### gui globals#################################################################

import project.classes as gc

#color position
current_color = gc.number(initial_value = np.nan, display = True, units_kind = 'color', ini = ['spectrometers', 'Spec', 'position (nm)'], save_to_ini_at_shutdown = True)
color_destination = gc.number(units_kind = 'color', ini = ['spectrometers', 'Spec', 'position (nm)'], import_from_ini = True)

#grating position
grating_tool_tip = '1: 150 grooves/mm, 1200 nm blaze\n2: 300 grooves/mm, 600 nm blaze'
current_grating = gc.string(initial_value = '?', display = True, ini = ['spectrometers', 'Spec', 'grating'], save_to_ini_at_shutdown = True)
current_grating.set_tool_tip(grating_tool_tip)
grating_destination = gc.combo(['1', '2'], ini = ['spectrometers', 'Spec', 'grating'], import_from_ini = True)
grating_destination.set_tool_tip(grating_tool_tip)

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
    control
    
#control########################################################################

class control():
    
    def __init__(self):
        self.ready = False
        print 'control.__init__'
        g.shutdown.add_method(self.shutdown)
        g.poll_timer.connect_to_timeout(self.poll)
        self.initialize_hardware()
        
    def initialize_hardware(self):
        q('initialize')
        
    def poll(self):
        pass
        #if not g.module_control.read(): q('poll')
        
    def set_hardware(self, destination):
        print 'set hardware'
        q('go_to', [destination])
    
    def wait_until_done(self, timeout = 10):
        '''
        timeout in seconds
        
        will only refer to timeout when busy.wait_for_update fires
        '''
        start_time = time.time()
        while busy.read():
            if time.time()-start_time < timeout:
                if not enqueued_actions.read(): q('check_busy')
                busy.wait_for_update()
            else: 
                g.logger.log('warning', 'Wait until done timed out', 'timeout set to {} seconds'.format(timeout))
                break
                
    def shutdown(self):
        if g.debug.read(): print 'MicroHR shutting down'
        g.logger.log('info', 'MicroHR shutdown')
        q('shutdown')
        self.wait_until_done()
        address_thread.quit()
        gui.stop()
        
control = control()

#gui############################################################################

class gui(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__
        address_obj.update_ui.connect(self.update)
        self.create_frame()
        
    def create_frame(self):
        
        layout_widget = custom_widgets.hardware_layout_widget('Monochromator', busy, address_obj.update_ui)
        layout = layout_widget.layout()

        input_table = custom_widgets.input_table(125)
        input_table.add('MicroHR', None)
        input_table.add('Grating', current_grating)
        input_table.add('Color', current_color)
        input_table.add('Grating Destination', grating_destination)
        input_table.add('Color Destination', color_destination)
        layout.addWidget(input_table)

        layout_widget.add_buttons(self.on_set, self.show_advanced)
        
        g.hardware_widget.add_to(layout_widget)
    
    def update(self):
        print 'update'
        pass
        
    def on_set(self):
        print 'on_set'
        control.set_hardware(destination.read())
    
    def show_advanced(self):
        pass
              
    def stop(self):
        pass
        
gui = gui()
### define ####################################################################

module_name = 'MOTORTUNE'

### import ####################################################################

import sys
import time

import numpy as np

import project.project_globals as g
scan_thread = g.scan_thread.read()

from PyQt4 import QtCore, QtGui
app = g.app.read()

import project.classes as pc
import project.widgets as pw

### import hardware control ###################################################

import spectrometers.spectrometers as spectrometers
import delays.delays as delays
import opas.opas as opas
import daq.daq as daq
import daq.current as daq_current

### scan globals ##############################################################

# These scan globals are used to communicated between the gui and the scan,
# which are running in different threads. All are mutex for this reason.

class fraction_complete:
    def __init__(self):
        self.value = 0
    def read(self):
        return self.value
    def write(self, value):  
        self.value = value
fraction_complete = fraction_complete()

class go:
    def __init__(self):
        self.value = False
    def read(self):
        return self.value
    def write(self, value):  
        self.value = value
go = go()

class going(QtCore.QMutex):
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
going = going()

class pause(QtCore.QMutex):
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
    def wait_for_update(self):
        if self.value: return self.WaitCondition.wait(self)
pause = pause()

class paused(QtCore.QMutex):
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
    def wait_for_update(self, timeout=100):
        if self.value: return self.WaitCondition.wait(self, msecs=timeout)
paused = paused()

### scan object ###############################################################

class scan(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal()
    
    @QtCore.pyqtSlot(list)
    def run(self, inputs):
        
        # unpack inputs -------------------------------------------------------
        
        scan_dictionary = inputs[0]
        
        daq_widget = inputs[1]

        # startup -------------------------------------------------------------

        g.module_control.write(True)
        going.write(True)
        fraction_complete.write(0.)
        g.logger.log('info', 'Scan begun', 'some info describing this scan')

        # scan ----------------------------------------------------------------

        spec_destinations = np.linspace(1100, 1620, 200)
        grating_destinations = np.linspace(34, 40, 40)
        bbo_destinations = np.linspace(35, 40, 80)
        
        npts = len(spec_destinations)*len(bbo_destinations)*len(grating_destinations)

        # initialize scan in daq
        daq.control.initialize_scan(daq_widget, fit=False)
        
        # do loop
        break_scan = False
        idx = 0
        for k in range(len(grating_destinations)):
            for j in range(len(bbo_destinations)):    
                inputs = [grating_destinations[k], bbo_destinations[j], 16.]
                OPA2.q.push('set_motors', inputs)    
                # slice index
                daq.control.index_slice(col='MicroHR')
                daq_current.gui.set_xlim(spec_destinations.min(), spec_destinations.max())    
                for i in range(len(spec_destinations)):
                    # set mono        
                    MicroHR.set_position(spec_destinations[i], 'nm')
                    # wait for all hardware
                    g.hardware_waits.wait()
                    # read from daq
                    daq.control.acquire()
                    daq.control.wait_until_daq_done()
                    # update
                    idx += 1
                    fraction_complete.write(float(idx)/float(npts))
                    self.update_ui.emit()
                    if not self.check_continue():
                        break_scan = True
                    if break_scan:
                        break
                if break_scan:
                    break
                # fit each slice
                #daq.control.fit('MicroHR', 'vai0 Mean')
            if break_scan:
                break
        
        #end-------------------------------------------------------------------

        print 'end'
        fraction_complete.write(1.)    
        going.write(False)
        g.module_control.write(False)
        g.logger.log('info', 'Scan done', 'some info describing this scan')
        self.update_ui.emit()
        self.done.emit()
        
    def check_continue(self):
        '''
        you should put this method into your scan loop wherever you want to check 
        for pause or stop commands from the main program
        
        at the very least this method MUST go into your innermost loop
        
        for loops, use it as follows: if not self.check_continue(): break
        '''
        while pause.read(): 
            paused.write(True)
            pause.wait_for_update()
        paused.write(False)
        return go.read()
        
#move scan to own thread      
scan_obj = scan()
scan_obj.moveToThread(scan_thread)
 
### gui #######################################################################

class gui(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)
        scan_obj.update_ui.connect(self.update)
        self.create_frame()
        self.create_advanced_frame()
        self.show_frame() #check once at startup
        g.shutdown.read().connect(self.stop)
        
    def create_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)
        
        allowed = [hardware.name for hardware in opas.hardwares]
        self.opa_combo = pc.Combo(allowed)
        
        input_table = pw.InputTable()
        input_table.add('OPA', self.opa_combo)
        layout.addWidget(input_table)
        
        motor_names = ['grating', 'bbo', 'mixer']
        input_table = pw.InputTable()
        for i in range(len(motor_names)):
            width = pc.Number()
            center = pc.Number()
            npts = pc.Number()
            input_table.add(motor_names[i], None)
            input_table.add('Width', width)
            input_table.add('Center', center)
            input_table.add('Number', npts)
        layout.addWidget(input_table)
        
        # daq widget
        self.daq_widget = daq.Widget()
        layout.addWidget(self.daq_widget)
        
        # go button
        self.go_button = pw.module_go_button()
        self.go_button.give_launch_scan_method(self.launch_scan)
        self.go_button.give_stop_scan_method(self.stop)  
        self.go_button.give_scan_complete_signal(scan_obj.done)
        self.go_button.give_pause_objects(pause, paused)
        
        layout.addWidget(self.go_button)
        
        layout.addStretch(1)
        
        self.frame = QtGui.QWidget()
        self.frame.setLayout(layout)
        
        g.module_widget.add_child(self.frame)
        g.module_combobox.add_module(module_name, self.show_frame)

    def create_advanced_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)

        self.advanced_frame = QtGui.QWidget()   
        self.advanced_frame.setLayout(layout)
        
        g.module_advanced_widget.add_child(self.advanced_frame)

    def show_frame(self):
        self.frame.hide()
        self.advanced_frame.hide()
        if g.module_combobox.get_text() == module_name:
            self.frame.show()
            self.advanced_frame.show()

    def launch_scan(self):        
        go.write(True)
        print 'running'
        scan_dictionary = {}
        inputs = [scan_dictionary, self.daq_widget]
        QtCore.QMetaObject.invokeMethod(scan_obj, 'run', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(list, inputs))    
        g.progress_bar.begin_new_scan_timer()        
        
    def update(self):
        g.progress_bar.set_fraction(fraction_complete.read())
              
    def stop(self):
        print 'stopping'
        go.write(False)
        while going.read(): going.wait_for_update()
        print 'stopped'
        
gui = gui()
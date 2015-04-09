#to do##########################################################################

#import#########################################################################

import sys

import numpy as np

import project.project_globals as g
scan_thread = g.scan_thread.read()

from PyQt4 import QtCore, QtGui
app = g.app.read()

import project.custom_widgets as custom_widgets     

#import hardware control########################################################

import spectrometers.spectrometers as mono
import daq.daq as daq

#scan globals###################################################################

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

#scan object####################################################################

class scan(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal()
    
    @QtCore.pyqtSlot(list)
    def run(self, inputs):

        #startup----------------------------------------------------------------

        g.module_control.write(True)
        going.write(True)
        fraction_complete.write(0.)
        g.logger.log('info', 'Scan begun', 'some info describing this scan')

        #scan-------------------------------------------------------------------

        destinations = np.linspace(1140, 1600, 50)

        for i in range(len(destinations)):

            mono.control.set_hardware(destinations[i])
            mono.control.wait_until_done()
            
            #check in with the rest of the program
            fraction_complete.write(float(i+1)/float(len(destinations)))
            self.update_ui.emit()
            if not self.check_continue(): break
            
        #end--------------------------------------------------------------------

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
        print '1'
        while pause.read(): 
            paused.write(True)
            print '2'
            pause.wait_for_update()
            print '3'
        paused.write(False)
        print '4'
        return go.read()
        
#move scan to own thread      
scan_obj = scan()
scan_obj.moveToThread(scan_thread)
 
### gui

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
        
        #daq widget
        daq_widget = daq.widget()
        layout.addWidget(daq_widget)
        
        #go button
        self.go_button = custom_widgets.module_go_button()
        self.go_button.give_launch_scan_method(self.launch_scan)
        self.go_button.give_stop_scan_method(self.stop)  
        self.go_button.give_scan_complete_signal(scan_obj.done)
        self.go_button.give_pause_objects(pause, paused)
        
        layout.addWidget(self.go_button)
        
        layout.addStretch(1)
        
        self.frame = QtGui.QWidget()
        self.frame.setLayout(layout)
        
        g.module_widget.add_child(self.frame)
        g.module_combobox.add_module('TEMPLATE', self.show_frame)

    def create_advanced_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)
       
        my_widget = QtGui.QLineEdit('this is a placeholder widget produced by template')
        my_widget.setAutoFillBackground(True)
        layout.addWidget(my_widget)
        
        self.advanced_frame = QtGui.QWidget()   
        self.advanced_frame.setLayout(layout)
        
        g.module_advanced_widget.add_child(self.advanced_frame)

    def show_frame(self):
        self.frame.hide()
        self.advanced_frame.hide()
        if g.module_combobox.get_text() == 'TEMPLATE':
            self.frame.show()
            self.advanced_frame.show()

    def launch_scan(self):        
        go.write(True)
        print 'running'
        inputs = ['hey this is inputs']
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
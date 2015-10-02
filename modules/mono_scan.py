### define ####################################################################

module_name = 'MONO SCAN'

### import ####################################################################

import sys
import time

import numpy as np

import matplotlib
matplotlib.pyplot.ioff()

import project.project_globals as g
import project.classes as pc
import project.widgets as pw

from PyQt4 import QtCore, QtGui
app = g.app.read()

import project.widgets as custom_widgets

import WrightTools as wt

### import hardware control ###################################################

import spectrometers.spectrometers as specs
MicroHR = specs.hardwares[0]
import delays.delays as delays
import opas.opas as opas
import daq.daq as daq

### objects ###################################################################

# to do with communication between threads
fraction_complete = pc.Mutex()
go = pc.Busy()
going = pc.Busy()
pause = pc.Busy()
paused = pc.Busy()

# control objects
start_color = pc.Number(initial_value=700, units='nm')
stop_color = pc.Number(initial_value=900, units='nm')
npts = pc.Number(initial_value=50, decimals=0)

### scan object ###############################################################

class scan(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal()
    
    @QtCore.pyqtSlot(list)
    def run(self, inputs):
        
        # unpack inputs -------------------------------------------------------
        
        scan_dictionary = inputs[0]
        daq_widget = inputs[1]
        gui = inputs[2]
                
        mono_destinations = np.linspace(start_color.read('wn'), stop_color.read('wn'), npts.read())
        
        # startup -------------------------------------------------------------

        g.module_control.write(True)
        going.write(True)
        fraction_complete.write(0.)
        g.logger.log('info', 'mono_scan begun', '')

        # scan ----------------------------------------------------------------

        # initialize scan in daq
        daq.control.initialize_scan(daq_widget, scan_origin=module_name, scan_axes=['wm'], fit=False)
        daq.gui.set_slice_xlim(start_color.read('nm'), stop_color.read('nm'))
        daq.control.index_slice(col='wm')
        
        # do loop

        break_scan = False
        idx = 0
        for i in range(len(mono_destinations)):
            MicroHR.set_position(mono_destinations[i], 'wn')
            g.hardware_waits.wait()            
            # read from daq
            daq.control.acquire()
            daq.control.wait_until_daq_done()
            # update
            idx += 1
            fraction_complete.write(float(idx)/float(npts.read()))
            self.update_ui.emit()
            if not self.check_continue():
                break_scan = True
            if break_scan:
                break
        
        #end-------------------------------------------------------------------

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
        
# scan object exists in the shared scan thread   
scan_obj = scan()
scan_thread = g.scan_thread.read()
scan_obj.moveToThread(scan_thread)
 
### gui #######################################################################

class gui(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)
        scan_obj.update_ui.connect(self.update)
        self.create_frame()
        self.create_advanced_frame()
        self.show_frame()  # check once at startup
        g.shutdown.read().connect(self.stop)
        scan_obj.done.connect(self.plot)
        
    def create_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)
        
        # input table
        input_table = pw.InputTable()
        input_table.add('Start', start_color)
        input_table.add('Stop', stop_color)
        input_table.add('Number', npts)
        layout.addWidget(input_table)
        
        # daq widget
        self.daq_widget = daq.Widget()
        layout.addWidget(self.daq_widget)
        
        # go button
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
        inputs = [scan_dictionary, self.daq_widget, self]
        QtCore.QMetaObject.invokeMethod(scan_obj, 'run', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(list, inputs))    
        g.progress_bar.begin_new_scan_timer()
        
    def plot(self):
        print 'plotting'
        data_path = daq.data_path.read()
        data_obj = wt.data.from_PyCMDS(data_path)
        artist = wt.artists.mpl_1D(data_obj)
        fname = data_path.replace('.data', '')
        artist.plot(fname=fname, autosave=True)
        
    def update(self):
        g.progress_bar.set_fraction(fraction_complete.read())
              
    def stop(self):
        print 'stopping'
        go.write(False)
        while going.read(): going.wait_for_update()
        print 'stopped'
        
gui = gui()

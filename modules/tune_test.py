### define ####################################################################

module_name = 'TUNE TEST'

### import ####################################################################

import sys
import time

import numpy as np

import project.project_globals as g
import project.classes as pc

from PyQt4 import QtCore, QtGui
app = g.app.read()

import project.widgets as custom_widgets

import WrightTools as wt

### import hardware control ###################################################

import spectrometers.spectrometers as specs
import delays.delays as delays
import opas.opas as opas
import daq.daq as daq
import daq.current as daq_current

### objects ###################################################################

# to do with communication between threads
fraction_complete = pc.Mutex()
go = pc.Busy()
going = pc.Busy()
pause = pc.Busy()
paused = pc.Busy()

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

        # startup -------------------------------------------------------------

        g.module_control.write(True)
        going.write(True)
        fraction_complete.write(0.)
        g.logger.log('info', 'Scan begun', 'some info describing this scan')

        # scan ----------------------------------------------------------------

        # initialize scan in daq
        daq.control.initialize_scan(daq_widget, scan_origin=module_name, scan_axes=['w1', 'wm'], fit=True)
        #daq_current.gui.set_xlim(spec_destinations.min(), spec_destinations.max())
        daq.control.index_slice(col='wm')
        
        # do loop
        '''
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

        daq.control.fit('wm', 'vai0_Mean')
        '''
        
        # plot ----------------------------------------------------------------
        
        '''
        data_path = daq.data_path.read()
        data_obj = wt.data.from_PyCMDS(data_path)
        artist = wt.artists.mpl_1D(data_obj)
        fname = data_path.replace('.data', '')
        artist.plot(fname=fname, autosave=True)
        '''

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
        
    def create_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)
        
        # input table
        input_table = custom_widgets.InputTable()
        allowed_opas = [hardware.name for hardware in opas.hardwares]
        self.opa_combo = pc.Combo(allowed_values=allowed_opas)
        input_table.add('OPA', self.opa_combo)
        input_table.add('Points', None)  
        self.tune_points = pc.Bool(initial_value=True)
        input_table.add('Use Tune Points', self.tune_points)
        self.initial_color = pc.Number(units='wn')
        input_table.add('Initial Color', self.initial_color)
        self.final_color = pc.Number(units='wn')
        input_table.add('Final Color', self.final_color)
        self.points_number = pc.Number(initial_value=21, decimals=0)
        input_table.add('Number', self.points_number)
        input_table.add('Spectrometer', None)
        self.mono_width = pc.Number(units='wn')
        input_table.add('Width', self.mono_width)
        self.mono_number = pc.Number(initial_value=21, decimals=0)
        input_table.add('Number', self.mono_number)
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
        
    def update(self):
        g.progress_bar.set_fraction(fraction_complete.read())
              
    def stop(self):
        print 'stopping'
        go.write(False)
        while going.read(): going.wait_for_update()
        print 'stopped'
        
gui = gui()

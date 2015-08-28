#to do##########################################################################

###import#########################################################################

import sys
import time

import numpy as np

import project.project_globals as g
import project.classes as pc
scan_thread = g.scan_thread.read()

from PyQt4 import QtCore, QtGui
app = g.app.read()

import project.widgets as custom_widgets

###import hardware control#######################################################

import spectrometers.spectrometers as spec
MicroHR = spec.hardwares[0]
import delays.delays as delay
D1 = delay.hardwares[0]
D2 = delay.hardwares[1]
D3 = None
import opas.opas as opa
OPA1 = None
OPA2 = opa.hardwares[0]
OPA3 = None
# import nds.nds as nd
ND1 = None
ND2 = None
ND3 = None
import daq.daq as daq
import daq.current as daq_current

###scan globals##################################################################

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

### Scan Perameters ###########################################################

limits = pc.NumberLimits(min_value=-10000, max_value=10000)
start_d = pc.Number(initial_value=-5, units='ps', limits=limits)
stop_d = pc.Number(initial_value=5, units='ps', limits=limits)
num_d = pc.Number(initial_value=-5, decimals=0)
delay_axis = 1

### scan object ###############################################################

class scan(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal()

    @QtCore.pyqtSlot(list)
    def run(self, inputs):

        ### unpack inputs

        scan_dictionary = inputs[0]

        daq_widget = inputs[1]

        ### startup

        g.module_control.write(True)
        going.write(True)
        fraction_complete.write(0.)
        g.logger.log('info', 'Scan begun', 'some info describing this scan')
        units = 'ps'

        ### scan

        delay_destinations = np.linspace(start_d.read(units), stop_d.read(units), num_d.read())

        npts = len(delay_destinations)

        # initialize scan in daq
        daq.control.initialize_scan(daq_widget, fit=True)
        daq_current.gui.set_xlim(delay_destinations.min(), delay_destinations.max())

        ### do loop
        break_scan = False
        idx = 0
        for i in range(len(delay_destinations)):
            # set delay
            if delay_axis == 1:
                D1.set_position(delay_destinations[i], units)
            elif delay_axis == 2:
                D2.set_position(delay_destinations[i], units)
            elif delay_axis == 3:
                D3.set_position(delay_destinations[i], units)
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

        daq.control.fit('MicroHR', 'vai0 Mean')


        ### end

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

        # input table one
        input_table = custom_widgets.InputTable()
        input_table.add('Initial', start_d)
        input_table.add('Final', stop_d)
        input_table.add('Number', num_d)
        layout.addWidget(input_table)

        # daq widget
        self.daq_widget = daq.Widget()
        layout.addWidget(self.daq_widget)

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
        g.module_combobox.add_module('Delay slice', self.show_frame)

    def create_advanced_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)

        my_widget = QtGui.QLineEdit('this is a placeholder widget produced by delay slice')
        my_widget.setAutoFillBackground(True)
        layout.addWidget(my_widget)

        self.advanced_frame = QtGui.QWidget()
        self.advanced_frame.setLayout(layout)

        g.module_advanced_widget.add_child(self.advanced_frame)

    def show_frame(self):
        self.frame.hide()
        self.advanced_frame.hide()
        if g.module_combobox.get_text() == 'Dealy slice':
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